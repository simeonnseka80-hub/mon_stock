from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
from openpyxl import Workbook
from .models import Produit, Mouvement, Facture
from .forms import MouvementForm

@login_required
def home(request):
    produits = Produit.objects.all()
    # Alerte si stock <= seuil
    for p in produits:
        p.alerte = p.stock_actuel() <= p.seuil_alerte
    return render(request, 'stock/home.html', {'produits': produits})

@login_required
def mouvement_list(request):
    mouvements = Mouvement.objects.select_related('produit').order_by('-date')
    # Filtres
    produit_id = request.GET.get('produit')
    type_mvt = request.GET.get('type')
    if produit_id:
        mouvements = mouvements.filter(produit_id=produit_id)
    if type_mvt in ('ENTREE', 'SORTIE'):
        mouvements = mouvements.filter(type_mouvement=type_mvt)

    produits = Produit.objects.all()
    context = {
        'mouvements': mouvements,
        'produits': produits,
        'selected_produit': produit_id,
        'selected_type': type_mvt,
    }
    return render(request, 'stock/mouvement_list.html', context)

@login_required
def mouvement_create(request):
    type_mvt = request.GET.get('type', Mouvement.ENTREE)
    if type_mvt not in (Mouvement.ENTREE, Mouvement.SORTIE):
        type_mvt = Mouvement.ENTREE

    initial = {'type_mouvement': type_mvt}
    if request.method == 'POST':
        form = MouvementForm(request.POST, initial=initial)
        if form.is_valid():
            mouvement = form.save(commit=False)

            # Définir prix_unitaire si non saisi
            if not mouvement.prix_unitaire:
                mouvement.prix_unitaire = mouvement.produit.prix_unitaire

            # Calculer prix_total
            mouvement.prix_total = mouvement.prix_unitaire * mouvement.quantite
            mouvement.save()

            # Gestion facture pour une sortie
            if mouvement.type_mouvement == Mouvement.SORTIE and form.cleaned_data.get('creer_facture'):
                Facture.objects.create(
                    mouvement=mouvement,
                    client_nom=form.cleaned_data['client_nom']
                )
                messages.success(request, "Sortie enregistrée et facture créée.")
                return redirect('facture_pdf', pk=mouvement.pk)
            else:
                messages.success(request, "Mouvement enregistré.")
                return redirect('mouvement_list')
    else:
        form = MouvementForm(initial=initial)

    return render(request, 'stock/mouvement_form.html', {
        'form': form,
        'type_mvt': type_mvt,
    })

@login_required
def facture_pdf(request, pk):
    mouvement = get_object_or_404(Mouvement, pk=pk)
    if mouvement.type_mouvement != Mouvement.SORTIE:
        messages.error(request, "Seules les sorties peuvent avoir une facture.")
        return redirect('mouvement_list')

    facture = getattr(mouvement, 'facture', None)
    if not facture:
        messages.error(request, "Aucune facture associée à ce mouvement.")
        return redirect('mouvement_list')

    produit = mouvement.produit
    prix_ht = mouvement.prix_unitaire or produit.prix_unitaire
    total_ht = mouvement.prix_total or (prix_ht * mouvement.quantite)
    tva_pct = produit.tva
    montant_tva = total_ht * tva_pct / 100
    total_ttc = total_ht + montant_tva

    context = {
        'mouvement': mouvement,
        'facture': facture,
        'produit': produit,
        'prix_ht': prix_ht,
        'total_ht': total_ht,
        'tva_pct': tva_pct,
        'montant_tva': montant_tva,
        'total_ttc': total_ttc,
    }
    html_string = render_to_string('stock/facture_template.html', context)
    result = BytesIO()
    pisa.CreatePDF(html_string, dest=result, encoding='utf-8')
    pdf_file = result.getvalue()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{facture.numero()}.pdf"'
    return response

@login_required
def export_excel(request):
    mouvements = Mouvement.objects.select_related('produit').order_by('-date')
    # Mêmes filtres
    produit_id = request.GET.get('produit')
    type_mvt = request.GET.get('type')
    if produit_id:
        mouvements = mouvements.filter(produit_id=produit_id)
    if type_mvt in ('ENTREE', 'SORTIE'):
        mouvements = mouvements.filter(type_mouvement=type_mvt)

    wb = Workbook()
    # Feuille "Grand Livre" (tous les mouvements)
    ws = wb.active
    ws.title = "Grand Livre"
    ws.append([
        "Date", "Type", "Produit", "Qté", "Unité",
        "Prix unitaire", "Prix total", "Commentaire",
        "Fournisseur", "N° fact. fournisseur", "Client", "N° facture client"
    ])
    for mvt in mouvements:
        client = ""
        fact_num = ""
        if mvt.type_mouvement == Mouvement.SORTIE and hasattr(mvt, 'facture'):
            client = mvt.facture.client_nom
            fact_num = mvt.facture.numero()
        ws.append([
            mvt.date.strftime("%d/%m/%Y %H:%M"),
            mvt.get_type_mouvement_display(),
            mvt.produit.nom,
            mvt.quantite,
            mvt.produit.unite_mesure,
            float(mvt.prix_unitaire or mvt.produit.prix_unitaire),
            float(mvt.prix_total or (mvt.prix_unitaire * mvt.quantite)),
            mvt.commentaire,
            mvt.fournisseur,
            mvt.numero_facture_fournisseur,
            client,
            fact_num,
        ])

    # Deuxième feuille : résumé des stocks
    ws2 = wb.create_sheet("Stock actuel")
    ws2.append(["Produit", "Unité", "Prix unitaire", "Stock", "Seuil alerte", "Alerte"])
    for produit in Produit.objects.all():
        stock = produit.stock_actuel()
        alerte = "OUI" if stock <= produit.seuil_alerte else "NON"
        ws2.append([
            produit.nom,
            produit.unite_mesure,
            float(produit.prix_unitaire),
            stock,
            produit.seuil_alerte,
            alerte
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=mouvements.xlsx'
    wb.save(response)
    return response

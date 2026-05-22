from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from xhtml2pdf import pisa
from openpyxl import Workbook
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.safestring import mark_safe

from .models import Produit, Mouvement, Facture
from .forms import MouvementForm


@login_required
def home(request):
    produits = Produit.objects.all()
    nb_produits = produits.count()
    valeur_stock = sum(p.stock_actuel() * p.prix_unitaire for p in produits)
    nb_critiques = sum(1 for p in produits if p.est_critique())
    mouvements_jour = Mouvement.objects.filter(date__date=timezone.now().date()).count()

    context = {
        'produits': produits,
        'nb_produits': nb_produits,
        'valeur_stock': valeur_stock,
        'nb_critiques': nb_critiques,
        'mouvements_jour': mouvements_jour,
    }
    return render(request, 'stock/home.html', context)


@login_required
def mouvement_list(request):
    mouvements = Mouvement.objects.select_related('produit').order_by('-date')
    produit_id = request.GET.get('produit')
    type_mvt = request.GET.get('type')
    search = request.GET.get('q', '')

    if produit_id:
        mouvements = mouvements.filter(produit_id=produit_id)
    if type_mvt in ('ENTREE', 'SORTIE'):
        mouvements = mouvements.filter(type_mouvement=type_mvt)
    if search:
        mouvements = mouvements.filter(
            Q(produit__nom__icontains=search) |
            Q(fournisseur__icontains=search) |
            Q(commentaire__icontains=search) |
            Q(numero_facture_fournisseur__icontains=search)
        )

    produits = Produit.objects.all()
    return render(request, 'stock/mouvement_list.html', {
        'mouvements': mouvements,
        'produits': produits,
        'selected_produit': produit_id,
        'selected_type': type_mvt,
        'search': search,
    })


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
            mouvement.type_mouvement = type_mvt

            if not mouvement.prix_unitaire:
                mouvement.prix_unitaire = mouvement.produit.prix_unitaire

            mouvement.save()   # ← Le mouvement est bien enregistré ici

            # Gestion de la facture pour une sortie
            if type_mvt == Mouvement.SORTIE and form.cleaned_data.get('creer_facture'):
                facture = Facture.objects.create(
                    mouvement=mouvement,
                    client_nom=form.cleaned_data['client_nom']
                )
                # Message avec lien vers le PDF
                url_pdf = reverse('facture_pdf', args=[mouvement.pk])
                messages.success(
                    request,
                    mark_safe(
                        f"✅ Sortie enregistrée et facture créée. "
                        f"<a href='{url_pdf}' class='underline font-semibold'>Télécharger la facture PDF</a>"
                    )
                )
                return redirect('mouvement_list')   # ← On reste sur la liste, pas de blocage
            else:
                messages.success(request, "Mouvement enregistré avec succès.")
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
    total_ht = facture.total_ht()
    total_ttc = facture.total_ttc()
    context = {
        'mouvement': mouvement,
        'facture': facture,
        'produit': produit,
        'total_ht': total_ht,
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
    produit_id = request.GET.get('produit')
    type_mvt = request.GET.get('type')
    if produit_id:
        mouvements = mouvements.filter(produit_id=produit_id)
    if type_mvt in ('ENTREE', 'SORTIE'):
        mouvements = mouvements.filter(type_mouvement=type_mvt)

    wb = Workbook()
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
            mvt.produit.get_unite_display(),
            float(mvt.prix_unitaire or mvt.produit.prix_unitaire),
            float(mvt.prix_total()),
            mvt.commentaire,
            mvt.fournisseur,
            mvt.numero_facture_fournisseur,
            client,
            fact_num,
        ])

    # Deuxième feuille
    ws2 = wb.create_sheet("Stock actuel")
    ws2.append(["Produit", "Unité", "Prix unitaire", "Stock", "Seuil alerte", "Alerte"])
    for p in Produit.objects.all():
        stock = p.stock_actuel()
        alerte = "OUI" if stock <= p.seuil_alerte else "NON"
        ws2.append([
            p.nom,
            p.get_unite_display(),
            float(p.prix_unitaire),
            stock,
            p.seuil_alerte,
            alerte
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=mouvements.xlsx'
    wb.save(response)
    return response
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.http import HttpResponse
from django.template.loader import render_to_string
from openpyxl import Workbook
from .models import Produit, Mouvement, Facture
from .forms import MouvementForm

# Méthode utilitaire pour le stock actuel (ajoutée au modèle plus bas)
# On la définit ici et on la rattache au modèle Produit.

def stock_actuel(self):
    entrees = self.mouvement_set.filter(type_mouvement=Mouvement.ENTREE).aggregate(Sum('quantite'))['quantite__sum'] or 0
    sorties = self.mouvement_set.filter(type_mouvement=Mouvement.SORTIE).aggregate(Sum('quantite'))['quantite__sum'] or 0
    return entrees - sorties

Produit.add_to_class('stock_actuel', stock_actuel)

@login_required
def home(request):
    produits = Produit.objects.all()
    # On passe les produits avec leur stock via la méthode
    return render(request, 'stock/home.html', {'produits': produits})

@login_required
def mouvement_list(request):
    mouvements = Mouvement.objects.select_related('produit').order_by('-date')
    # Filtres simples
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
    type_mvt = request.GET.get('type', Mouvement.ENTREE)  # par défaut entrée
    if type_mvt not in (Mouvement.ENTREE, Mouvement.SORTIE):
        type_mvt = Mouvement.ENTREE

    initial = {'type_mouvement': type_mvt}
    if request.method == 'POST':
        form = MouvementForm(request.POST, initial=initial)
        if form.is_valid():
            mouvement = form.save()
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
        messages.error(request, "Aucune facture associée à ce mouvement. Créez d'abord la sortie avec l'option facture.")
        return redirect('mouvement_list')

    context = {
        'mouvement': mouvement,
        'facture': facture,
        'produit': mouvement.produit,
        'total': mouvement.produit.prix_unitaire * mouvement.quantite,
    }
    html_string = render_to_string('stock/facture_template.html', context)
    try:
        from weasyprint import HTML
    except OSError:
        messages.error(
            request,
            "Impossible de générer le PDF: les bibliothèques système de WeasyPrint "
            "(GTK/Pango) ne sont pas installées ou ne sont pas dans le PATH."
        )
        return redirect('mouvement_list')

    pdf_file = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="{facture.numero()}.pdf"'
    return response

@login_required
def export_excel(request):
    mouvements = Mouvement.objects.select_related('produit').order_by('-date')
    # Appliquer mêmes filtres que la liste
    produit_id = request.GET.get('produit')
    type_mvt = request.GET.get('type')
    if produit_id:
        mouvements = mouvements.filter(produit_id=produit_id)
    if type_mvt in ('ENTREE', 'SORTIE'):
        mouvements = mouvements.filter(type_mouvement=type_mvt)

    wb = Workbook()
    ws = wb.active
    ws.title = "Mouvements"
    ws.append(["Date", "Type", "Produit", "Quantité", "Prix unitaire", "Commentaire", "Client (si facture)"])

    for mvt in mouvements:
        client = ""
        if mvt.type_mouvement == Mouvement.SORTIE and hasattr(mvt, 'facture'):
            client = mvt.facture.client_nom
        ws.append([
            mvt.date.strftime("%d/%m/%Y %H:%M"),
            mvt.get_type_mouvement_display(),
            mvt.produit.nom,
            mvt.quantite,
            float(mvt.produit.prix_unitaire),
            mvt.commentaire,
            client,
        ])

    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=mouvements.xlsx'
    wb.save(response)
    return response

from django import forms
from .models import Mouvement, Produit

class MouvementForm(forms.ModelForm):
    # Champs supplémentaires pour la facture (seulement si type = SORTIE)
    client_nom = forms.CharField(max_length=200, required=False, label="Nom du client")
    creer_facture = forms.BooleanField(required=False, label="Créer une facture PDF", initial=True)

    class Meta:
        model = Mouvement
        fields = [
            'produit', 'type_mouvement', 'quantite',
            'prix_unitaire', 'prix_total', 'commentaire',
            'fournisseur', 'numero_facture_fournisseur'
        ]
        widgets = {
            'type_mouvement': forms.HiddenInput(),
            'prix_unitaire': forms.NumberInput(attrs={'step': '0.01'}),
            'prix_total': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        type_mvt = self.initial.get('type_mouvement', Mouvement.ENTREE)

        # Selon le type, on cache/affiche les champs appropriés
        if type_mvt == Mouvement.SORTIE:
            # Sortie : masquer les champs d'achat
            self.fields.pop('fournisseur')
            self.fields.pop('numero_facture_fournisseur')
            # Rendre le client obligatoire
            self.fields['client_nom'].required = True
            self.fields['creer_facture'].widget = forms.CheckboxInput(attrs={'checked': 'checked'})
        else:
            # Entrée : masquer les champs de facture client
            self.fields.pop('client_nom')
            self.fields.pop('creer_facture')
            # Rendre fournisseur obligatoire (optionnel, on peut le laisser facultatif)
            # self.fields['fournisseur'].required = True  # décommente si tu veux forcer

    def clean(self):
        cleaned_data = super().clean()
        type_mvt = cleaned_data.get('type_mouvement')
        quantite = cleaned_data.get('quantite')
        produit = cleaned_data.get('produit')

        # Vérifier le stock disponible pour une sortie
        if type_mvt == Mouvement.SORTIE and produit and quantite:
            stock_actuel = produit.stock_actuel()
            if quantite > stock_actuel:
                raise forms.ValidationError(
                    f"Stock insuffisant pour {produit.nom} ({stock_actuel} disponible(s))."
                )

        # Si prix unitaire non fourni, on prendra celui du produit dans la vue
        return cleaned_data

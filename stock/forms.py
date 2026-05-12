from django import forms
from .models import Mouvement, Produit

class MouvementForm(forms.ModelForm):
    # Champs supplémentaires pour la facture (seulement si type = SORTIE)
    client_nom = forms.CharField(max_length=200, required=False, label="Nom du client")
    creer_facture = forms.BooleanField(required=False, label="Créer une facture PDF", initial=True)

    class Meta:
        model = Mouvement
        fields = ['produit', 'type_mouvement', 'quantite', 'commentaire']
        widgets = {
            'type_mouvement': forms.HiddenInput()  # sera défini via l'URL
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Si le type est SORTIE, on affiche les champs de facture, sinon on les cache
        if self.initial.get('type_mouvement') == Mouvement.SORTIE:
            self.fields['client_nom'].required = True
            self.fields['creer_facture'].widget = forms.CheckboxInput(attrs={'checked': 'checked'})
        else:
            self.fields.pop('client_nom')
            self.fields.pop('creer_facture')

    def clean(self):
        cleaned_data = super().clean()
        type_mvt = cleaned_data.get('type_mouvement')
        quantite = cleaned_data.get('quantite')
        produit = cleaned_data.get('produit')

        # Vérifier le stock disponible en cas de sortie
        if type_mvt == Mouvement.SORTIE and produit and quantite:
            stock_actuel = produit.stock_actuel()  # méthode ajoutée au modèle Produit
            if quantite > stock_actuel:
                raise forms.ValidationError(
                    f"Stock insuffisant pour {produit.nom} ({stock_actuel} disponible(s))."
                )
        return cleaned_data
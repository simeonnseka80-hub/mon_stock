from django import forms
from .models import Mouvement

class MouvementForm(forms.ModelForm):
    client_nom = forms.CharField(max_length=200, required=False, label="Nom du client")
    creer_facture = forms.BooleanField(required=False, label="Créer une facture PDF", initial=True)

    class Meta:
        model = Mouvement
        fields = [
            'produit', 'quantite', 'prix_unitaire', 'commentaire',
            'fournisseur', 'numero_facture_fournisseur'
        ]
        widgets = {
            'prix_unitaire': forms.NumberInput(attrs={'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Récupérer le type depuis les données initiales ou POST
        type_mvt = self.initial.get('type_mouvement', Mouvement.ENTREE)
        if self.data and 'type_mouvement' in self.data:
            type_mvt = self.data['type_mouvement']

        # Appliquer des classes CSS à tous les champs
        for field_name in self.fields:
            if isinstance(self.fields[field_name], forms.BooleanField):
                self.fields[field_name].widget.attrs.update({
                    'class': 'h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded'
                })
            else:
                self.fields[field_name].widget.attrs.update({
                    'class': 'mt-1 block w-full border border-gray-300 rounded-md shadow-sm py-2 px-3 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm'
                })

        # Afficher/masquer les champs selon le type de mouvement
        if type_mvt == Mouvement.SORTIE:
            self.fields.pop('fournisseur', None)
            self.fields.pop('numero_facture_fournisseur', None)
            self.fields['client_nom'].required = True
            self.fields['creer_facture'].widget.attrs['checked'] = 'checked'
        else:  # Entrée
            self.fields.pop('client_nom', None)
            self.fields.pop('creer_facture', None)

    def clean(self):
        cleaned_data = super().clean()
        type_mvt = self.initial.get('type_mouvement')
        if self.data and 'type_mouvement' in self.data:
            type_mvt = self.data['type_mouvement']

        quantite = cleaned_data.get('quantite')
        produit = cleaned_data.get('produit')

        if type_mvt == Mouvement.SORTIE and produit and quantite:
            stock_actuel = produit.stock_actuel()
            if quantite > stock_actuel:
                raise forms.ValidationError(
                    f"Stock insuffisant pour {produit.nom} ({stock_actuel} disponible(s))."
                )
        return cleaned_data
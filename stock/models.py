from django.db import models

class Produit(models.Model):
    nom = models.CharField(max_length=200)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nom

class Mouvement(models.Model):
    ENTREE = 'ENTREE'
    SORTIE = 'SORTIE'
    TYPE_CHOICES = [
        (ENTREE, 'Entrée'),
        (SORTIE, 'Sortie'),
    ]

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantite = models.PositiveIntegerField()
    date = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    def __str__(self):
        return f"{self.type_mouvement} {self.produit.nom} x{self.quantite}"

class Facture(models.Model):
    mouvement = models.OneToOneField(
        Mouvement,
        on_delete=models.CASCADE,
        limit_choices_to={'type_mouvement': Mouvement.SORTIE}
    )
    client_nom = models.CharField(max_length=200)
    date_facture = models.DateTimeField(auto_now_add=True)

    def numero(self):
        return f"FACT-{self.id:04d}"

    def __str__(self):
        return f"Facture {self.numero()} - {self.client_nom}"
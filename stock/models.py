from django.db import models
from django.db.models import Sum

class Produit(models.Model):
    UNITE_CHOICES = [
        ('U', 'Unité(s)'),
        ('KG', 'Kilogramme(s)'),
        ('L', 'Litre(s)'),
        ('M', 'Mètre(s)'),
    ]

    nom = models.CharField(max_length=200, verbose_name="Désignation")
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    unite = models.CharField(max_length=2, choices=UNITE_CHOICES, default='U', verbose_name="Unité de mesure")
    taux_tva = models.DecimalField(max_digits=4, decimal_places=2, default=16.00, verbose_name="TVA (%)")
    seuil_alerte = models.PositiveIntegerField(default=5, verbose_name="Seuil d’alerte")

    def stock_actuel(self):
        entrees = self.mouvement_set.filter(type_mouvement='ENTREE').aggregate(Sum('quantite'))['quantite__sum'] or 0
        sorties = self.mouvement_set.filter(type_mouvement='SORTIE').aggregate(Sum('quantite'))['quantite__sum'] or 0
        return entrees - sorties

    def est_critique(self):
        return self.stock_actuel() <= self.seuil_alerte

    def __str__(self):
        return f"{self.nom} ({self.prix_unitaire} $/{self.get_unite_display()})"


class Mouvement(models.Model):
    ENTREE = 'ENTREE'
    SORTIE = 'SORTIE'
    TYPE_CHOICES = [(ENTREE, 'Entrée'), (SORTIE, 'Sortie')]

    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    type_mouvement = models.CharField(max_length=10, choices=TYPE_CHOICES)
    quantite = models.PositiveIntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    date = models.DateTimeField(auto_now_add=True)
    commentaire = models.TextField(blank=True)

    # Champs pour les entrées (achats)
    fournisseur = models.CharField(max_length=200, blank=True, verbose_name="Nom du fournisseur")
    numero_facture_fournisseur = models.CharField(max_length=100, blank=True, verbose_name="N° facture fournisseur")

    def prix_total(self):
        if self.prix_unitaire:
            return self.prix_unitaire * self.quantite
        return self.produit.prix_unitaire * self.quantite

    def save(self, *args, **kwargs):
        if not self.prix_unitaire:
            self.prix_unitaire = self.produit.prix_unitaire
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.get_type_mouvement_display()} - {self.produit.nom} x{self.quantite}"


class Facture(models.Model):
    mouvement = models.OneToOneField(
        Mouvement,
        on_delete=models.CASCADE,
        limit_choices_to={'type_mouvement': 'SORTIE'}
    )
    client_nom = models.CharField(max_length=200)
    date_facture = models.DateTimeField(auto_now_add=True)

    def numero(self):
        return f"FACT-{self.id:04d}"

    def total_ht(self):
        return self.mouvement.prix_total()

    def total_ttc(self):
        return self.total_ht() * (1 + self.mouvement.produit.taux_tva / 100)

    def __str__(self):
        return f"Facture {self.numero()} – {self.client_nom}"
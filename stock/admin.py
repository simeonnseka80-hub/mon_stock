
from django.contrib import admin
from .models import Produit, Mouvement, Facture

admin.site.register(Produit)
admin.site.register(Mouvement)
admin.site.register(Facture)
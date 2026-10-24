from django.contrib import admin

from .models import (IndicadorEducacion, IndicadorRegion, IndicadorZona,
                     IngresoDecil, ResumenNacional)

# Registrar los modelos para revisarlos en Django Admin
admin.site.register(IndicadorRegion)
admin.site.register(IndicadorZona)
admin.site.register(IndicadorEducacion)
admin.site.register(IngresoDecil)
admin.site.register(ResumenNacional)

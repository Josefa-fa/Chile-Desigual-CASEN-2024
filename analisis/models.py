from django.db import models


# Indicadores comunes a un grupo de personas (región o zona).
# Es abstracto: no crea tabla, solo comparte los campos con los modelos hijos.
class IndicadoresBase(models.Model):
    poblacion = models.BigIntegerField("Población estimada")
    pobreza_ingresos = models.FloatField("Pobreza por ingresos (%)")
    pobreza_extrema = models.FloatField("Pobreza extrema (%)")
    pobreza_multidimensional = models.FloatField("Pobreza multidimensional (%)")
    ingreso_mediano = models.IntegerField("Ingreso per cápita mediano ($)")
    escolaridad_adultos = models.FloatField("Escolaridad de adultos (años)")

    class Meta:
        abstract = True


# Listado 1: una fila por región, ordenada de norte a sur
class IndicadorRegion(IndicadoresBase):
    orden = models.PositiveSmallIntegerField("Orden norte-sur")
    nombre = models.CharField("Región", max_length=40)

    class Meta:
        ordering = ["orden"]
        verbose_name = "indicador por región"
        verbose_name_plural = "indicadores por región"

    def __str__(self):
        return self.nombre


# Listado 2: una fila por zona (urbano / rural)
class IndicadorZona(IndicadoresBase):
    nombre = models.CharField("Zona", max_length=20)
    hacinamiento = models.FloatField("Hogares con hacinamiento (%)")

    class Meta:
        verbose_name = "indicador por zona"
        verbose_name_plural = "indicadores por zona"

    def __str__(self):
        return self.nombre


# Listado 3: una fila por nivel educacional de las personas de 18 años o más
class IndicadorEducacion(models.Model):
    orden = models.PositiveSmallIntegerField("Orden")
    nivel = models.CharField("Nivel educacional", max_length=40)
    poblacion = models.BigIntegerField("Adultos estimados")
    porcentaje_adultos = models.FloatField("% de los adultos")
    ingreso_mediano = models.IntegerField("Ingreso per cápita mediano ($)")
    ingreso_medio = models.IntegerField("Ingreso per cápita medio ($)")
    pobreza_ingresos = models.FloatField("Pobreza por ingresos (%)")

    class Meta:
        ordering = ["orden"]
        verbose_name = "indicador por nivel educacional"
        verbose_name_plural = "indicadores por nivel educacional"

    def __str__(self):
        return self.nivel


# Datos para la curva de Lorenz: ingreso de cada decil de la población
class IngresoDecil(models.Model):
    decil = models.PositiveSmallIntegerField("Decil", unique=True)
    ingreso_medio = models.IntegerField("Ingreso per cápita medio ($)")
    participacion = models.FloatField("% del ingreso total")

    class Meta:
        ordering = ["decil"]
        verbose_name = "ingreso por decil"
        verbose_name_plural = "ingreso por decil"

    def __str__(self):
        return f"Decil {self.decil}"


# Indicadores nacionales (una sola fila) que se muestran en la página de inicio
class ResumenNacional(models.Model):
    poblacion = models.BigIntegerField("Población estimada")
    registros = models.IntegerField("Registros de la encuesta")
    gini = models.FloatField("Índice de Gini")
    pobreza_ingresos = models.FloatField("Pobreza por ingresos (%)")
    pobreza_extrema = models.FloatField("Pobreza extrema (%)")
    pobreza_multidimensional = models.FloatField("Pobreza multidimensional (%)")
    ingreso_mediano = models.IntegerField("Ingreso per cápita mediano ($)")
    escolaridad_adultos = models.FloatField("Escolaridad de adultos (años)")

    class Meta:
        verbose_name = "resumen nacional"
        verbose_name_plural = "resumen nacional"

    def __str__(self):
        return "CASEN 2024 - nacional"

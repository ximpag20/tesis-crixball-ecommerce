from django import forms
from .models import Producto, Talla, ProductoTalla
from django.forms.models import inlineformset_factory


class ProductoForm(forms.ModelForm):
    tallas = forms.ModelMultipleChoiceField(
        queryset=Talla.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # Usa checkbox para selección múltiple
        required=False,
        label="Selecciona las tallas disponibles"
    )

    class Meta:
        model = Producto
        # Elimina 'cantidad_disponible' del formulario, ya que no existe en el modelo Producto
        fields = ['nombre_pro', 'id_rama', 'detalle_pro', 'imagen_pro']
        widgets = {
            'nombre_pro': forms.TextInput(attrs={'class': 'form-control'}),
            'id_rama': forms.Select(attrs={'class': 'form-control'}),
            'detalle_pro': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'imagen_pro': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }
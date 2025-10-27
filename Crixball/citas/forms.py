from django import forms
from .models import Reserva
from catalogo.models import Talla, Producto, ProductoTalla
from datetime import datetime, timedelta

class ReservaForm(forms.ModelForm):
    id_pro = forms.ModelChoiceField(
        queryset=Producto.objects.all(),
        widget=forms.HiddenInput(),  # Campo oculto para manejar el producto seleccionado
        required=True,
        error_messages={'required': 'Debe seleccionar un producto para continuar.'}
    )
    talla = forms.CharField(
        required=True,
        error_messages={'required': 'Debe seleccionar una talla válida.'}
    )

    class Meta:
        model = Reserva
        fields = ['id_pro', 'talla', 'cantidad_reservada', 'date_reserva', 'hora_reserva', 'comentario']
        widgets = {
            'cantidad_reservada': forms.NumberInput(attrs={
                'min': '1', 
                'class': 'form-control',
                'id': 'cantidad_reservada',
                'disabled': True
            }),
            'date_reserva': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'hora_reserva': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'comentario': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_talla(self):
        """
        Validar que la talla seleccionada sea válida y esté asociada al producto.
        """
        talla_nombre = self.cleaned_data.get('talla')

        if not talla_nombre:
            raise forms.ValidationError("Debe seleccionar una talla válida.")

        # Convertir el valor de `talla` en una instancia de Talla
        try:
            talla_obj = Talla.objects.get(talla=talla_nombre)
            return talla_obj
        except Talla.DoesNotExist:
            raise forms.ValidationError("La talla seleccionada no es válida.")
    
    def clean(self):
        cleaned_data = super().clean()
        fecha = cleaned_data.get('date_reserva')
        hora = cleaned_data.get('hora_reserva')

        if fecha and hora:
            nueva_inicio = datetime.combine(fecha, hora)
            nueva_fin = nueva_inicio + timedelta(minutes=30)

            reservas = Reserva.objects.filter(date_reserva=fecha)
            for reserva in reservas:
                existente_inicio = datetime.combine(reserva.date_reserva, reserva.hora_reserva)
                existente_fin = existente_inicio + timedelta(minutes=30)

                # Verificamos traslape de intervalos
                if (nueva_inicio < existente_fin) and (existente_inicio < nueva_fin):
                    self.add_error(
                        'hora_reserva',
                        f"Ya existe una reserva entre {existente_inicio.time()} y {existente_fin.time()}. "
                        f"Debe elegir una hora que no se traslape."
                    )
                    break

from django import forms
from registro.models import Usuario
from django.contrib.auth.hashers import check_password

class ActualizarDatosForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nombre", "apellido", "email", "tel", "birth"]
        widgets = {
            "nombre": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nombre", "disabled": "disabled"}),
            "apellido": forms.TextInput(attrs={"class": "form-control", "placeholder": "Apellido", "disabled": "disabled"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "Correo Electrónico", "disabled": "disabled"}),
            "tel": forms.TextInput(attrs={"class": "form-control", "placeholder": "Teléfono", "disabled": "disabled"}),
            "birth": forms.DateInput(
                attrs={"class": "form-control", "type": "date", "disabled": "disabled"}, format="%Y-%m-%d"
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Convertir la fecha al formato YYYY-MM-DD si existe
        if self.instance and self.instance.birth:
            self.initial["birth"] = self.instance.birth.strftime("%Y-%m-%d")

class CambiarContrasenaForm(forms.Form):
    contrasena_actual = forms.CharField(
        label="Contraseña actual",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Contraseña actual"}),
    )
    nueva_contrasena = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Nueva contraseña"}),
    )
    confirmar_contrasena = forms.CharField(
        label="Confirmar nueva contraseña",
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Confirmar nueva contraseña"}),
    )

    def __init__(self, usuario, *args, **kwargs):
        self.usuario = usuario
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        contrasena_actual = cleaned_data.get("contrasena_actual")
        nueva_contrasena = cleaned_data.get("nueva_contrasena")
        confirmar_contrasena = cleaned_data.get("confirmar_contrasena")

        # Validar contraseña actual
        if not check_password(contrasena_actual, self.usuario.contrasenia):  # Nota: usa el campo contrasenia
            self.add_error("contrasena_actual", "La contraseña actual es incorrecta.")

        # Validar que la nueva contraseña y la confirmación coincidan
        if nueva_contrasena != confirmar_contrasena:
            self.add_error("confirmar_contrasena", "Las contraseñas no coinciden.")

        # Validar que la nueva contraseña sea diferente de la actual
        if contrasena_actual and nueva_contrasena == contrasena_actual:
            self.add_error("nueva_contrasena", "La nueva contraseña no puede ser igual a la actual.")

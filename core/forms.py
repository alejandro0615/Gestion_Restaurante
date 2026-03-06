from django import forms  # API de formularios de Django.
from django.contrib.auth import get_user_model  # Acceso al modelo de usuario para validar correo único global.

from .models import Cliente, Producto, Promocion  # Modelos locales usados por los formularios.


# Clases base de Tailwind para inputs de texto, correo y selects.
CAMPO_BASE = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200'

# Clases para áreas de texto de varias líneas.
CAMPO_TEXTO_GRANDE = 'mt-1 w-full rounded-xl border border-slate-300 bg-white px-3 py-2 text-sm shadow-sm outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-200 min-h-24'

# Clases para checkboxes en selección múltiple.
CHECKBOX_BASE = 'h-4 w-4 rounded border-slate-300 text-blue-600 transition focus:ring-2 focus:ring-blue-400'


class PedidoPublicoForm(forms.Form):
    nombre = forms.CharField(max_length=120, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Nombre del cliente.
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': CAMPO_BASE}))  # Correo válido del cliente.
    telefono = forms.CharField(max_length=30, required=False, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Teléfono opcional.
    tipo_servicio = forms.ChoiceField(
        choices=(
            ('sitio', 'Consumo en el sitio'),
            ('domicilio', 'Entrega a domicilio'),
        ),
        widget=forms.Select(attrs={'class': CAMPO_BASE}),
    )  # Campo de selección entre sitio/domicilio.
    direccion_entrega = forms.CharField(max_length=250, required=False, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Dirección si es domicilio.
    notas = forms.CharField(widget=forms.Textarea(attrs={'class': CAMPO_TEXTO_GRANDE}), required=False)  # Observaciones del pedido.
    productos = forms.ModelMultipleChoiceField(
        queryset=Producto.objects.filter(disponible=True),  # Solo productos activos de la carta.
        widget=forms.CheckboxSelectMultiple(attrs={'class': CHECKBOX_BASE}),
        required=False,
    )
    promocion = forms.ModelChoiceField(
        queryset=Promocion.objects.filter(activa=True),  # Solo promociones vigentes.
        required=False,
        empty_label='Sin promoción',
        widget=forms.Select(attrs={'class': CAMPO_BASE}),
    )

    def clean(self):
        cleaned_data = super().clean()
        tipo_servicio = (cleaned_data.get('tipo_servicio') or '').strip().lower()
        direccion_entrega = (cleaned_data.get('direccion_entrega') or '').strip()

        if tipo_servicio == 'domicilio':
            if not direccion_entrega:
                self.add_error('direccion_entrega', 'La dirección de entrega es obligatoria para domicilio.')
            else:
                # Validación básica de dirección correcta: longitud mínima y datos de ubicación.
                if len(direccion_entrega) < 10:
                    self.add_error('direccion_entrega', 'La dirección es muy corta. Ingresa una dirección más completa.')
                if not any(char.isdigit() for char in direccion_entrega):
                    self.add_error('direccion_entrega', 'La dirección debe incluir al menos un número (ej: #45-20).')

        # Si es consumo en sitio, se ignora cualquier dirección enviada.
        if tipo_servicio == 'sitio':
            cleaned_data['direccion_entrega'] = ''

        return cleaned_data


class ClienteRegistroForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se exige cédula y teléfono para evitar registros incompletos o ambiguos.
        self.fields['cedula'].required = True
        self.fields['telefono'].required = True

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('El correo es obligatorio.')

        queryset_cliente = Cliente.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk:
            queryset_cliente = queryset_cliente.exclude(pk=self.instance.pk)
        if queryset_cliente.exists():
            raise forms.ValidationError('Ya existe un cliente con este correo.')

        User = get_user_model()
        queryset_user = User.objects.filter(email__iexact=email)
        if self.instance and self.instance.pk and self.instance.user_id:
            queryset_user = queryset_user.exclude(pk=self.instance.user_id)
        if queryset_user.exists():
            raise forms.ValidationError('Este correo ya está en uso por otro usuario del sistema.')

        return email

    def clean_cedula(self):
        cedula = (self.cleaned_data.get('cedula') or '').strip()
        if not cedula:
            raise forms.ValidationError('La cédula es obligatoria.')

        queryset = Cliente.objects.filter(cedula=cedula)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Ya existe un cliente con esta cédula.')

        return cedula

    def clean_telefono(self):
        telefono = (self.cleaned_data.get('telefono') or '').strip()
        if not telefono:
            raise forms.ValidationError('El teléfono es obligatorio.')

        queryset = Cliente.objects.filter(telefono=telefono)
        if self.instance and self.instance.pk:
            queryset = queryset.exclude(pk=self.instance.pk)
        if queryset.exists():
            raise forms.ValidationError('Ya existe un cliente con este teléfono.')

        return telefono

    class Meta:
        model = Cliente  # Modelo que persiste estos datos.
        fields = ['nombre', 'cedula', 'telefono', 'email']  # Campos editables en pantalla.
        widgets = {
            'nombre': forms.TextInput(attrs={'class': CAMPO_BASE}),
            'cedula': forms.TextInput(attrs={'class': CAMPO_BASE}),
            'telefono': forms.TextInput(attrs={'class': CAMPO_BASE}),
            'email': forms.EmailInput(attrs={'class': CAMPO_BASE}),
        }


class CambiarContraseñaForm(forms.Form):
    # Formulario para que clientes cambien su contraseña desde el perfil.
    contraseña_actual = forms.CharField(
        label='Contraseña actual',
        widget=forms.PasswordInput(attrs={'class': CAMPO_BASE, 'placeholder': 'Tu contraseña actual'}),
    )
    contraseña_nueva = forms.CharField(
        label='Contraseña nueva',
        widget=forms.PasswordInput(attrs={'class': CAMPO_BASE, 'placeholder': 'Nueva contraseña (mín. 8 caracteres)'}),
        min_length=8,
    )
    contraseña_nueva_confirmacion = forms.CharField(
        label='Confirmar contraseña nueva',
        widget=forms.PasswordInput(attrs={'class': CAMPO_BASE, 'placeholder': 'Repite la nueva contraseña'}),
        min_length=8,
    )
    
    def clean(self):
        # Valida que las dos nuevas contraseñas coincidan.
        cleaned_data = super().clean()
        contraseña_nueva = cleaned_data.get('contraseña_nueva')
        contraseña_nueva_confirmacion = cleaned_data.get('contraseña_nueva_confirmacion')
        
        if contraseña_nueva and contraseña_nueva_confirmacion:
            if contraseña_nueva != contraseña_nueva_confirmacion:
                raise forms.ValidationError('Las contraseñas nuevas no coinciden.')
        
        return cleaned_data
class CanjearCodigoForm(forms.Form):
    cedula = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Identifica cliente por documento.
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': CAMPO_BASE}))  # Valida coincidencia con correo registrado.
    codigo = forms.CharField(max_length=16, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Código enviado por correo para canje.


class CanjearCodigoClienteForm(forms.Form):
    codigo = forms.CharField(
        max_length=16,
        widget=forms.TextInput(
            attrs={
                'class': CAMPO_BASE,
                'placeholder': 'Ej. AB12CD34',
            }
        ),
    )  # Código recibido por correo; es de un solo uso.


class EnviarCodigoForm(forms.Form):
    cedula = forms.CharField(max_length=20, widget=forms.TextInput(attrs={'class': CAMPO_BASE}))  # Cédula del cliente destino.
    email = forms.EmailField(widget=forms.EmailInput(attrs={'class': CAMPO_BASE}))  # Correo del cliente destino.


class RegistroClientePublicoForm(forms.Form):
    nombre = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={'class': CAMPO_BASE}),
    )  # Nombre del cliente para crear su perfil y usuario.
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': CAMPO_BASE}),
    )  # Correo del cliente (se usa para login y envío de contraseña).

    def clean_email(self):
        email = (self.cleaned_data.get('email') or '').strip().lower()
        if not email:
            raise forms.ValidationError('El correo es obligatorio.')

        if Cliente.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo ya está registrado en clientes.')

        User = get_user_model()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Este correo ya está en uso en el sistema.')

        return email


class ProductoMenuForm(forms.ModelForm):
    class Meta:
        model = Producto  # Edición operativa de producto desde vista web de menús.
        fields = ['nombre', 'descripcion', 'precio', 'categoria', 'disponible', 'disponible_todos_los_dias']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': CAMPO_BASE}),
            'descripcion': forms.Textarea(attrs={'class': CAMPO_TEXTO_GRANDE}),
            'precio': forms.NumberInput(attrs={'class': CAMPO_BASE, 'step': '0.01', 'min': '0'}),
            'categoria': forms.Select(attrs={'class': CAMPO_BASE}),
            'disponible': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'}),
            'disponible_todos_los_dias': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500'}),
        }

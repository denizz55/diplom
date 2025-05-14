from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Review, Booking

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

class ConcertFilterForm(forms.Form):
    date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'}),
        label="Дата концерта"
    )

class ReviewForm(forms.ModelForm):
    RATING_CHOICES = [(i, f"{i} звезд{'а' if i == 1 else 'ы' if 2 <= i <= 4 else ''}") for i in range(1, 6)]
    
    rating = forms.ChoiceField(
        choices=RATING_CHOICES,
        widget=forms.RadioSelect(attrs={'class': 'star-rating'}),
        label="Оценка"
    )
    
    comment = forms.CharField(
        widget=forms.Textarea(attrs={'placeholder': 'Поделитесь своим мнением о концерте...', 'rows': 4}),
        label="Отзыв"
    )
    
    class Meta:
        model = Review
        fields = ['rating', 'comment']

class BookingForm(forms.ModelForm):
    full_name = forms.CharField(
        max_length=255, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
        label="ФИО"
    )
    phone = forms.CharField(
        max_length=20, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 999 123-45-67'}),
        label="Телефон"
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'example@mail.ru'}),
        label="Электронная почта"
    )
    
    class Meta:
        model = Booking
        fields = ['full_name', 'phone', 'email']

class PaymentForm(forms.Form):
    card_number = forms.CharField(
        max_length=19,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '1234 5678 9012 3456',
            'data-mask': '0000 0000 0000 0000'
        }),
        label="Номер карты"
    )
    card_holder = forms.CharField(
        max_length=255,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'IVAN IVANOV'}),
        label="Имя владельца карты"
    )
    expiry_date = forms.CharField(
        max_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '12/25',
            'data-mask': '00/00'
        }),
        label="Срок действия (ММ/ГГ)"
    )
    cvv = forms.CharField(
        max_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '123',
            'type': 'password',
            'data-mask': '000'
        }),
        label="CVV/CVC"
    )
    
    def clean_card_number(self):
        card_number = self.cleaned_data.get('card_number').replace(' ', '')
        if not card_number.isdigit() or len(card_number) != 16:
            raise forms.ValidationError("Введите корректный номер карты (16 цифр)")
        return card_number
    
    def clean_expiry_date(self):
        expiry_date = self.cleaned_data.get('expiry_date')
        if not '/' in expiry_date:
            raise forms.ValidationError("Введите дату в формате ММ/ГГ")
        
        try:
            month, year = expiry_date.split('/')
            month = int(month)
            year = int(year)
            
            if month < 1 or month > 12:
                raise forms.ValidationError("Месяц должен быть от 1 до 12")
            
            if year < 23:  # Примерно для 2023 года
                raise forms.ValidationError("Срок действия карты истек")
                
        except (ValueError, IndexError):
            raise forms.ValidationError("Введите корректную дату")
            
        return expiry_date
    
    def clean_cvv(self):
        cvv = self.cleaned_data.get('cvv')
        if not cvv.isdigit() or len(cvv) != 3:
            raise forms.ValidationError("CVV должен содержать 3 цифры")
        return cvv

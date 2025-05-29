from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import uuid

class Concert(models.Model):
    name = models.CharField(max_length=255)
    date = models.DateTimeField()
    description = models.TextField()
    image = models.ImageField(upload_to='concert_images/')
    price = models.IntegerField(default=2000, verbose_name='Стоимость (₽)')
    vip_price = models.IntegerField(default=4000, verbose_name='Стоимость VIP (₽)')

    def delete(self, *args, **kwargs):
        Booking.objects.filter(seat__concert=self).delete()
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

class Seat(models.Model):
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE, related_name='seats')
    row = models.IntegerField()
    seat_number = models.IntegerField()
    is_booked = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    is_vip = models.BooleanField(default=False, verbose_name='VIP-место')

    class Meta:
        unique_together = ('concert', 'row', 'seat_number')

    def __str__(self):
        return f"Ряд {self.row}, Место {self.seat_number} ({'Занято' if self.is_booked else 'Свободно'})"


@receiver(post_save, sender=Concert)
def create_seating_chart(sender, instance, created, **kwargs):
    if created:
        for row in range(1, 11): 
            for seat in range(1, 13):  
                is_vip = row in [4, 5, 6] and seat in [5, 6, 7, 8]
                Seat.objects.create(concert=instance, row=row, seat_number=seat, is_vip=is_vip)

class Booking(models.Model):
    seat = models.OneToOneField(Seat, related_name='booking', on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    booking_date = models.DateTimeField(auto_now_add=True)
    # Новые поля для контактной информации
    full_name = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    # Платежная информация
    is_paid = models.BooleanField(default=False)
    payment_id = models.CharField(max_length=100, null=True, blank=True)
    
    def __str__(self):
        user_name = self.user.username if self.user else self.full_name
        return f"{user_name} booked {self.seat} for {self.seat.concert.name}"

class Payment(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='payment')
    payment_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField(auto_now_add=True)
    is_successful = models.BooleanField(default=False)
    card_last_digits = models.CharField(max_length=4, null=True, blank=True)
    
    def __str__(self):
        return f"Payment {self.payment_id} for {self.booking}"
    
    @classmethod
    def generate_payment_id(cls):
        return str(uuid.uuid4())

class Review(models.Model):
    concert = models.ForeignKey(Concert, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure a user can only review a concert once
        unique_together = ('concert', 'user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s review for {self.concert.name} ({self.rating} stars)"

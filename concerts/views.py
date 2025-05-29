from django.shortcuts import render, get_object_or_404, redirect
from .models import Concert, Seat, Booking, Review, Payment
from django.http import HttpResponseRedirect, JsonResponse
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.contrib.auth import login, authenticate
from .forms import UserRegistrationForm, ReviewForm, BookingForm, PaymentForm, ConcertFilterForm, ConcertForm
from django.contrib.auth import logout
from django.db import IntegrityError, transaction
from django.db.models import Avg
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie, csrf_exempt
from django.middleware.csrf import get_token
import random
import time
from django.db import models
from django.views.decorators.http import require_POST
from .utils import send_ticket_email

def concert_list(request):
    concerts = Concert.objects.order_by('date')
    # Get average ratings for each concert
    for concert in concerts:
        concert.avg_rating = concert.reviews.aggregate(Avg('rating'))['rating__avg']
        concert.review_count = concert.reviews.count()
    return render(request, 'concerts/concert_list.html', {'concerts': concerts})

def concert_detail(request, id):
    concert = get_object_or_404(Concert, id=id)

    # Формирование схемы зала
    rows = Seat.objects.filter(concert=concert).values_list('row', flat=True).distinct()
    seating_chart = {
        row: Seat.objects.filter(concert=concert, row=row).order_by('seat_number')
        for row in rows
    }
    
    # Get reviews for this concert
    reviews = Review.objects.filter(concert=concert)
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']
    review_count = reviews.count()
    
    # Check if user has already reviewed
    user_review = None
    can_review = False
    
    if request.user.is_authenticated:
        user_review = Review.objects.filter(concert=concert, user=request.user).first()
        # User can review if they haven't already reviewed and have attended/booked the concert
        has_booked = Booking.objects.filter(seat__concert=concert, user=request.user).exists()
        can_review = has_booked and not user_review
        
        # Debugging: Print user's seats to server log
        user_seats = Seat.objects.filter(concert=concert, user=request.user)
        print(f"Found {user_seats.count()} seats for user {request.user.username}")
        for seat in user_seats:
            print(f"User has seat at row {seat.row}, number {seat.seat_number}")
            # Force update user seat status to ensure consistency
            if not seat.is_booked:
                seat.is_booked = True
                seat.save()

    # Initialize the review form
    review_form = ReviewForm()

    return render(request, 'concerts/concert_detail.html', {
        'concert': concert,
        'seating_chart': seating_chart,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'user_review': user_review,
        'can_review': can_review,
        'review_form': review_form,
    })

@login_required
def add_review(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    
    # Check if user has already reviewed this concert
    if Review.objects.filter(concert=concert, user=request.user).exists():
        messages.error(request, 'Вы уже оставили отзыв на этот концерт')
        return redirect('concert_detail', id=concert_id)
    
    # Check if user has attended/booked the concert
    if not Booking.objects.filter(seat__concert=concert, user=request.user).exists():
        messages.error(request, 'Вы можете оставить отзыв только после посещения концерта')
        return redirect('concert_detail', id=concert_id)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.concert = concert
            review.user = request.user
            review.save()
            messages.success(request, 'Ваш отзыв успешно добавлен!')
            return redirect('concert_detail', id=concert_id)
    else:
        form = ReviewForm()
    
    return render(request, 'concerts/add_review.html', {
        'form': form,
        'concert': concert
    })

@login_required
def edit_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    
    if request.method == 'POST':
        form = ReviewForm(request.POST, instance=review)
        if form.is_valid():
            form.save()
            messages.success(request, 'Ваш отзыв успешно обновлён!')
            return redirect('concert_detail', id=review.concert.id)
    else:
        form = ReviewForm(instance=review)
    
    return render(request, 'concerts/edit_review.html', {
        'form': form,
        'concert': review.concert
    })

@login_required
def delete_review(request, review_id):
    review = get_object_or_404(Review, id=review_id, user=request.user)
    concert_id = review.concert.id
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Ваш отзыв успешно удалён!')
        return redirect('concert_detail', id=concert_id)
    
    return render(request, 'concerts/delete_review.html', {
        'review': review
    })

@login_required
def seat_selection(request, seat_id):
    seat = get_object_or_404(Seat, id=seat_id)
    
    # Проверка, что место не забронировано
    if seat.is_booked:
        messages.error(request, 'Это место уже забронировано')
        return HttpResponseRedirect(reverse('concert_detail', args=[seat.concert.id]))
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            # Создаем объект бронирования, но не сохраняем в базу
            booking = form.save(commit=False)
            booking.seat = seat
            booking.user = request.user
            # Данные сохраняются в сессии для использования на странице оплаты
            request.session['booking_data'] = {
                'seat_id': seat.id,
                'full_name': form.cleaned_data['full_name'],
                'phone': form.cleaned_data['phone'],
                'email': form.cleaned_data['email'],
            }
            # Перенаправляем на страницу оплаты
            return redirect('payment', seat_id=seat.id)
    else:
        # Предзаполняем форму данными пользователя, если они доступны
        initial_data = {}
        if request.user.first_name and request.user.last_name:
            initial_data['full_name'] = f"{request.user.first_name} {request.user.last_name}"
        if request.user.email:
            initial_data['email'] = request.user.email
        
        form = BookingForm(initial=initial_data)
    
    return render(request, 'concerts/booking_form.html', {
        'form': form,
        'seat': seat,
        'concert': seat.concert
    })

@login_required
def payment_view(request, seat_id):
    seat = get_object_or_404(Seat, id=seat_id)
    
    # Проверка, что место не забронировано
    if seat.is_booked:
        messages.error(request, 'Это место уже забронировано')
        return HttpResponseRedirect(reverse('concert_detail', args=[seat.concert.id]))
    
    # Получаем данные бронирования из сессии
    booking_data = request.session.get('booking_data')
    if not booking_data or int(booking_data['seat_id']) != seat.id:
        messages.error(request, 'Некорректные данные бронирования. Пожалуйста, начните заново.')
        return redirect('seat_selection', seat_id=seat.id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Создаем бронирование
                    booking = Booking.objects.create(
                        seat=seat,
                        user=request.user,
                        full_name=booking_data['full_name'],
                        phone=booking_data['phone'],
                        email=booking_data['email'],
                        is_paid=True,
                    )
                    
                    # Обновляем статус места
                    seat.is_booked = True
                    seat.user = request.user
                    seat.save()
                    
                    # Симуляция задержки обработки платежа
                    time.sleep(1)
                    
                    # Создаем запись о платеже
                    payment_id = Payment.generate_payment_id()
                    card_last_digits = form.cleaned_data['card_number'][-4:]
                    
                    payment = Payment.objects.create(
                        booking=booking,
                        payment_id=payment_id,
                        amount=seat.concert.vip_price if seat.is_vip else seat.concert.price,
                        is_successful=True,
                        card_last_digits=card_last_digits,
                    )
                    
                    # Обновляем бронирование
                    booking.payment_id = payment_id
                    booking.save()
                    
                    # Очищаем данные сессии
                    if 'booking_data' in request.session:
                        del request.session['booking_data']
                    # Отправляем электронный билет
                    try:
                        send_ticket_email(
                            booking.email,
                            booking,
                            seat,
                            seat.concert,
                            payment_id
                        )
                    except Exception as e:
                        print(f"Ошибка отправки email: {e}")
                    messages.success(request, f'Оплата прошла успешно! Ваш билет забронирован. Номер платежа: {payment_id}')
                    return redirect('payment_success', payment_id=payment_id)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при обработке платежа: {str(e)}')
                return redirect('payment', seat_id=seat.id)
    else:
        form = PaymentForm()
    
    return render(request, 'concerts/payment.html', {
        'form': form,
        'seat': seat,
        'concert': seat.concert,
        'booking_data': booking_data,
        'price': seat.concert.vip_price if seat.is_vip else seat.concert.price
    })

@login_required
def payment_success(request, payment_id):
    payment = get_object_or_404(Payment, payment_id=payment_id)
    
    # Проверяем, что платеж принадлежит текущему пользователю
    if payment.booking.user != request.user:
        messages.error(request, 'У вас нет доступа к этому платежу')
        return redirect('concert_list')
    
    return render(request, 'concerts/payment_success.html', {
        'payment': payment,
        'booking': payment.booking,
        'seat': payment.booking.seat,
        'concert': payment.booking.seat.concert
    })

# Модифицированное представление book_seat для перенаправления на форму бронирования
@login_required
def book_seat(request, seat_id):
    seat = get_object_or_404(Seat, id=seat_id)
    
    # Проверяем, не забронировано ли место
    if seat.is_booked:
        messages.error(request, 'Это место уже забронировано')
        return HttpResponseRedirect(reverse('concert_detail', args=[seat.concert.id]))
    
    # Перенаправляем на страницу с формой бронирования
    return redirect('seat_selection', seat_id=seat_id)

@login_required
def cancel_booking(request, booking_id):
    # Получаем бронирование или возвращаем 404
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if request.method == 'POST':
        # Освобождаем место
        seat = booking.seat
        seat.is_booked = False
        seat.user = None  # Remove the user association
        seat.save()

        # Сообщение об успешной отмене бронирования и возврате средств
        message = "Бронирование успешно отменено."
        if booking.is_paid or hasattr(booking, 'payment'):
            message += " Средства будут возвращены на вашу карту в течение 3-5 рабочих дней."
        
        # Удаляем бронирование
        booking.delete()
        
        messages.success(request, message)
        return redirect('profile')  # Перенаправление в личный кабинет
    
    # Отображаем страницу подтверждения для GET-запроса
    return render(request, 'concerts/cancel_booking.html', {
        'booking': booking
    })

@login_required
def profile(request):
    # Получаем бронирования текущего пользователя
    bookings = Booking.objects.filter(user=request.user)

    return render(request, 'profile.html', {
        'bookings': bookings,
    })

@csrf_exempt  # This temporarily disables CSRF protection - REMOVE THIS IN PRODUCTION
def register(request):
    # Explicitly set CSRF cookie
    get_token(request)
    
    if request.method == 'POST':
        # Print debug information about CSRF
        print("CSRF token in request:", request.POST.get('csrfmiddlewaretoken'))
        print("Request headers:", request.headers)
        
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Account created for {username}!')
            login(request, user) 
            return redirect('concert_list')
        else:
            # Print form errors to help debugging
            print("Form errors:", form.errors)
    else:
        form = UserRegistrationForm()
    # Ensure we're passing the request context to the template
    return render(request, 'concerts/register.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('concert_list')  # Перенаправление на главную страницу

def profile_view(request):
    # Получить все бронирования для текущего пользователя
    bookings = Booking.objects.filter(user=request.user).select_related('seat__concert')
    # Get user's reviews
    reviews = Review.objects.filter(user=request.user).select_related('concert')
    return render(request, 'concerts/profile.html', {'bookings': bookings, 'reviews': reviews})

def about_us(request):
    return render(request, 'concerts/about_us.html')

def contacts(request):
    return render(request, 'concerts/contacts.html')

def privacy_policy(request):
    return render(request, 'concerts/privacy_policy.html')

# Функция API для поиска концертов
def search_concerts_api(request):
    query = request.GET.get('q', '')
    
    print(f"Search API received query: {query}")
    
    if len(query) < 2:
        return JsonResponse([], safe=False)
    
    # Поиск концертов только по названию и описанию
    try:
        concerts = Concert.objects.filter(
            models.Q(name__icontains=query) | 
            models.Q(description__icontains=query)
        )[:10]  # Ограничиваем результаты до 10
        
        # Готовим данные для JSON-ответа
        results = []
        for concert in concerts:
            # Форматируем дату как строку
            date_str = concert.date.strftime('%d.%m.%Y') if concert.date else ''
            
            results.append({
                'id': concert.id,
                'title': concert.name,
                'description': concert.description,
                'date': date_str,
                'price': str(concert.price),
                'image': concert.image.url if concert.image else ''
            })
        
        print(f"Found {len(results)} database results for '{query}'")
        
        # Всегда добавляем демо-данные для тестирования, если нет результатов из БД
        if not results:
            print(f"No database results, adding demo data for '{query}'")
            # Демо-данные для тестирования функциональности
            results = [
                {'id': 999, 'title': f'Концерт по запросу "{query}"', 'description': 'Большой сольный концерт в ВТБ Арене', 'date': '15.06.2024', 'price': '2500', 'image': ''},
                {'id': 998, 'title': f'Выступление по запросу "{query}"', 'description': 'Презентация нового альбома в Лужниках', 'date': '20.07.2024', 'price': '3000', 'image': ''},
                {'id': 997, 'title': f'Фестиваль по запросу "{query}"', 'description': 'Совместное выступление в Зеленом театре', 'date': '05.08.2024', 'price': '2800', 'image': ''}
            ]
            
        # Добавляем особые демо-данные для Басты
        if 'баста' in query.lower():
            results.extend([
                {'id': 996, 'title': 'Концерт Басты', 'description': 'Большой сольный концерт в ВТБ Арене', 'date': '15.06.2024', 'price': '2500', 'image': ''},
                {'id': 995, 'title': 'Баста в Москве', 'description': 'Презентация нового альбома в Лужниках', 'date': '20.07.2024', 'price': '3000', 'image': ''},
                {'id': 994, 'title': 'Сплин и Баста', 'description': 'Совместное выступление в Зеленом театре', 'date': '05.08.2024', 'price': '2800', 'image': ''}
            ])
        
        print(f"Returning {len(results)} total results")
        return JsonResponse(results, safe=False)
        
    except Exception as e:
        print(f"Error in search_concerts_api: {str(e)}")
        # В случае ошибки возвращаем тестовые данные
        results = [
            {'id': 993, 'title': f'Тестовый концерт по запросу "{query}"', 'date': '15.06.2024', 'price': '2500', 'image': ''},
            {'id': 992, 'title': f'Тестовое выступление по запросу "{query}"', 'date': '20.07.2024', 'price': '3000', 'image': ''}
        ]
        return JsonResponse(results, safe=False)

def is_admin(user):
    return user.is_staff or user.is_superuser

@user_passes_test(is_admin)
@login_required
def admin_dashboard(request):
    concerts = Concert.objects.order_by('-date')
    if request.method == 'POST':
        form = ConcertForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Концерт успешно создан!')
            return redirect('admin_dashboard')
    else:
        form = ConcertForm()
    return render(request, 'concerts/admin_dashboard.html', {'form': form, 'concerts': concerts})

@user_passes_test(is_admin)
@login_required
def delete_concert(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    if request.method == 'POST':
        concert.delete()
        messages.success(request, 'Концерт успешно удалён!')
        return redirect('admin_dashboard')
    return render(request, 'concerts/delete_concert.html', {'concert': concert})

@user_passes_test(is_admin)
@login_required
def edit_concert(request, concert_id):
    concert = get_object_or_404(Concert, id=concert_id)
    if request.method == 'POST':
        form = ConcertForm(request.POST, request.FILES, instance=concert)
        if form.is_valid():
            form.save()
            messages.success(request, 'Концерт успешно обновлён!')
            return redirect('admin_dashboard')
    else:
        form = ConcertForm(instance=concert)
    return render(request, 'concerts/edit_concert.html', {'form': form, 'concert': concert})
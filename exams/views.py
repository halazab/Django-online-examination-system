from django.shortcuts import render, redirect
from .models import Exams, Question, Option, Result, ShortAnswer, GradingInterval
from .forms import ExamForm, QuestionForm, OptionForm, ShortAnswerForm
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from users.models import Profile
from .models import UserResponse
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
import json
from .models import Transaction, UserExam, Subscription, PaymentTransaction
import requests
from datetime import datetime, timedelta
import uuid
from django.utils import timezone
from django.contrib import messages
from django.db.models import Avg, Max, Count, F
from django.db.models.functions import TruncMonth

# def teacher_dashboard(request):
#     profile = Profile.objects.get(user=request.user)
#     exams = Exams.objects.filter(created_by=request.user)
#     return render(request, 'teacher_dashboard.html', {'exams': exams, 'profile': profile})

def student_dashboard(request):
    exams = Exams.objects.all()
    return render(request, 'student_dashboard.html', {'exams': exams})


# @login_required
# def create_question(request):
#     if request.method == 'POST':
#         # Create a form instance and populate it with data from the request
#         question_form = QuestionForm(request.POST)
        
#         if question_form.is_valid():
#             # Save the question first
#             question = question_form.save(commit=False)
#             question.save()  # Now save the question to the database
            
#             # Handle options
#             options_data = [
#                 (question_form.cleaned_data['option_a'], True),
#                 (question_form.cleaned_data['option_b'], False),
#                 (question_form.cleaned_data['option_c'], False),
#                 (question_form.cleaned_data['option_d'], False),
#             ]
            
#             options = []
#             for i, (text, is_correct) in enumerate(options_data):
#                 if text:  # Check if the option text is not empty
#                     options.append(Option(question=question, text=text, is_correct=is_correct))

#             # Create options in bulk
#             if options:
#                 Option.objects.bulk_create(options)  # Create options in bulk

#             return redirect('create_question')  # Redirect to a question list or other page
#     else:
#         question_form = QuestionForm()

#     # Retrieve all exams
#     exams = Exams.objects.all()  # Query to get all exams

#     return render(request, 'create_question.html', {'question_form': question_form, 'exams': exams})
def view_results(request, exam_id):
    results = Result.objects.filter(exam_id=exam_id)
    return render(request, 'view_results.html', {'results': results})
def auto_grade(result):
    score = 0
    answers = result.answers  # Assuming answers are stored in JSON format
    for question in Question.objects.filter(exam=result.exam):
        if question.question_type == 'MCQ':
            correct_option = Option.objects.filter(question=question, is_correct=True).first()
            if answers.get(str(question.id)) == correct_option.id:
                score += 1
        elif question.question_type == 'TF':
            # Logic for True/False grading
            pass
        elif question.question_type == 'SA':
            # Logic for Short Answer grading
            pass
    result.score = score
    result.save()
@login_required
def student_analytics(request):
    results = Result.objects.filter(user=request.user)
    # Prepare data for the graph
    data = {
        'exams': [result.exam.title for result in results],
        'scores': [result.score for result in results],
    }
    return render(request, 'student_analytics.html', {'data': data})
def exam_detail(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = exam.question_set.all()
    return render(request, 'exam_detail.html', {'exam': exam, 'questions': questions})
def exam_list(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    exams = Exams.objects.all()  # Fetch all exams
    return render(request, 'exam_list.html', {'exams': exams, 'profile': profile, "exam":exam})  # Render the exam list template
def exam_questions(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)

    context = {
        'exam': exam,
        'questions': questions,
    }
    
    return render(request, 'exam_questions.html', context)

@login_required
def take_exam(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)
    
    user_exam, created = UserExam.objects.get_or_create(
        user=request.user,
        exam=exam,
        defaults={'completed': False}
    )

    if user_exam.completed:
        messages.warning(request, 'You have already completed this exam.')
        return redirect('exam_list')

    if request.method == 'POST':
        try:
            answers = {}
            correct_answers = 0
            total_questions = questions.count()

            for question in questions:
                answer_key = f'question_{question.id}'
                if answer_key in request.POST:
                    selected_option = request.POST[answer_key].strip()
                    answers[str(question.id)] = selected_option

                    # Save user response
                    UserResponse.objects.create(
                        user=request.user,  # Add user to UserResponse
                        question=question,
                        selected_option=selected_option
                    )

                    # Compare answers case-insensitively
                    if selected_option.lower() == question.correct_answer.strip().lower():
                        correct_answers += 1

            # Calculate percentage correctly
            percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
            percentage = round(percentage, 2)  # Round to 2 decimal places

            # Save the result with the percentage score, not the raw score
            Result.objects.create(
                user=request.user,
                exam=exam,
                score=percentage,  # Save percentage as score
                answers=json.dumps(answers)
            )

            # Mark exam as completed
            user_exam.completed = True
            user_exam.save()

            # Check if user passed
            passed = percentage >= exam.passing_percentage
            
            context = {
                'exam': exam,
                'score': percentage,  # Use percentage here
                'total_questions': total_questions,
                'correct_answers': correct_answers,
                'percentage': percentage,
                'passed': passed
            }
            
            messages.success(request, 'Exam completed successfully!')
            return redirect('exam_result', exam_id=exam.id)

        except Exception as e:
            messages.error(request, f'Error submitting exam: {str(e)}')
            return redirect('take_exam', exam_id=exam_id)

    context = {
        'exam': exam,
        'questions': questions,
    }
    return render(request, 'take_exam.html', context)

def exam_results(request, exam_id):
    profile = Profile.objects.get(user=request.user)
    exam = get_object_or_404(Exams, id=exam_id)
    questions = Question.objects.filter(exam=exam)
    
    # Get the user's result for this exam
    try:
        result = Result.objects.get(user=request.user, exam=exam)
    except Result.DoesNotExist:
        result = None

    responses = []
    correct_answers = 0
    
    for question in questions:
        try:
            response = UserResponse.objects.get(
                question=question,
                user=request.user  # Make sure to filter by user
            )
            
            # Compare answers directly with question's correct answer
            is_correct = response.selected_option.strip().lower() == question.correct_answer.strip().lower()
            if is_correct:
                correct_answers += 1
            
            responses.append({
                'question': question,
                'selected_option': response.selected_option,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct
            })
        except UserResponse.DoesNotExist:
            continue

    total_questions = questions.count()
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score >= exam.passing_percentage

    context = {
        'exam': exam,
        'responses': responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score': round(score, 2),
        'passed': passed,
        'profile': profile,
        'result': result
    }
    
    return render(request, 'exam_results.html', context)
@login_required
def payment_view(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)

    if not exam.is_premium:
        return redirect('exam_detail', exam_id=exam.id)  # Redirect if the exam is not premium

    if request.method == 'POST':
        # Payment processing logic here
        amount = int(exam.price * 100)  # Chapa expects the amount in cents
        email = request.user.email

        # Create a transaction record
        transaction = Transaction.objects.create(
            user=request.user,
            exam=exam,
            amount=exam.price,
            currency='ETB',  # or whatever currency you are using
            email=email,
            status='pending'
        )

        # Chapa payment URL
        headers = {
            'Authorization': 'Bearer YOUR_SECRET_KEY',
        }
        
        # Prepare payment request
        payment_data = {
            "amount": amount,
            "currency": "ETB",
            "email": email,
            "transaction_id": str(transaction.id),
            "callback_url": "http://127.0.0.1:8000/payment/callback/"
        }

        response = requests.post('https://api.chapa.co/v1/transaction/initialize', headers=headers, json=payment_data)

        if response.status_code == 200:
            payment_url = response.json().get('data').get('url')
            return redirect(payment_url)  # Redirect user to Chapa payment page
        else:
            # Handle payment error
            return render(request, 'payment_error.html', {'error': response.json()})

    return render(request, 'payment.html', {'exam': exam})

def get_chapa_secret_key():
    return settings.CHAPA_SECRET_KEY

@login_required
def subscription_plans(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    plans = {
        'basic': {'price': 1000, 'duration': 30, 'features': ['Access to basic exams', 'Limited question bank']},
        'premium': {'price': 2500, 'duration': 30, 'features': ['Access to all exams', 'Full question bank', 'Analytics']},
        'enterprise': {'price': 5000, 'duration': 30, 'features': ['Custom exams', 'Priority support', 'Advanced analytics']},
    }
    return render(request, 'exams/subscription_plans.html', {'plans': plans, 'profile': profile, "exam":exam})

@login_required
def initialize_payment(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            subscription_type = data.get('subscription_type')
            amount = data.get('amount')
            
            # Generate unique transaction reference
            tx_ref = str(uuid.uuid4())
            
            # Prepare headers for Chapa API
            headers = {
                "Authorization": f"Bearer {get_chapa_secret_key()}",
                "Content-Type": "application/json"
            }
            
            # Prepare payload for Chapa
            payload = {
                "amount": str(amount),
                "currency": "ETB",
                "email": request.user.email,
                "first_name": request.user.first_name or "Customer",
                "last_name": request.user.last_name or "Name",
                "tx_ref": tx_ref,
                "callback_url": f"{settings.BASE_URL}/payment/verify/{tx_ref}/",
                "return_url": f"{settings.BASE_URL}/payment/success/",
                "customization[title]": f"Online Exam {subscription_type} Subscription",
                "customization[description]": f"Payment for {subscription_type} subscription"
            }
            
            # Initialize payment with Chapa
            response = requests.post(
                "https://api.chapa.co/v1/transaction/initialize",
                json=payload,
                headers=headers
            )
            
            if response.status_code == 200:
                response_data = response.json()
                
                # Create subscription record
                end_date = datetime.now() + timedelta(days=30)
                subscription = Subscription.objects.create(
                    user=request.user,
                    subscription_type=subscription_type,
                    amount=amount,
                    end_date=end_date,
                    transaction_reference=tx_ref
                )
                
                # Create payment transaction record
                PaymentTransaction.objects.create(
                    user=request.user,
                    subscription=subscription,
                    amount=amount,
                    transaction_reference=tx_ref
                )
                
                return JsonResponse({
                    'status': 'success',
                    'checkout_url': response_data['data']['checkout_url']
                })
            
            return JsonResponse({
                'status': 'error',
                'message': 'Failed to initialize payment'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            })
    
    # Handle GET requests
    return JsonResponse({
        'status': 'error',
        'message': 'Method not allowed'
    }, status=405)

@csrf_exempt
def verify_payment(request, tx_ref):
    try:
        headers = {
            "Authorization": f"Bearer {get_chapa_secret_key()}",
        }
        
        response = requests.get(
            f"https://api.chapa.co/v1/transaction/verify/{tx_ref}",
            headers=headers
        )
        
        if response.status_code == 200:
            verification_data = response.json()
            
            if verification_data.get('status') == 'success':
                try:
                    # Get transaction and subscription
                    transaction = PaymentTransaction.objects.get(transaction_reference=tx_ref)
                    subscription = transaction.subscription
                    
                    # Update transaction status
                    transaction.status = 'success'
                    transaction.save()
                    
                    # Update subscription status
                    subscription.is_active = True
                    subscription.save()
                    
                    # Update user profile - Fix: Don't use login_required here
                    profile = Profile.objects.get(user=transaction.user)
                    profile.subscription_status = 'premium'
                    profile.subscription_end_date = subscription.end_date
                    profile.save()
                    
                    # Redirect to success page with user context
                    return redirect('payment_success')  # Make sure this URL name exists
                    
                except Exception as e:
                    print(f"Error in payment verification: {str(e)}")
                    return JsonResponse({
                        'status': 'error',
                        'message': f'Invalid transaction: {str(e)}'
                    })
        
        return JsonResponse({
            'status': 'error',
            'message': 'Payment verification failed'
        })
        
    except Exception as e:
        print(f"Exception in verify_payment: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@login_required
def payment_success(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    return render(request, 'exams/payment_success.html', {'exam': exam, 'profile': profile})

@login_required
def subscription_status(request):
    try:
        active_subscription = Subscription.objects.get(
            user=request.user,
            is_active=True,
            end_date__gt=datetime.now()
        )
        return JsonResponse({
            'status': 'success',
            'has_subscription': True,
            'subscription_type': active_subscription.subscription_type,
            'end_date': active_subscription.end_date.strftime('%Y-%m-%d')
        })
    except Subscription.DoesNotExist:
        return JsonResponse({
            'status': 'success',
            'has_subscription': False
        })

def recent_exams(request):
    # Get exams from the last 30 days
    recent_date = timezone.now() - timedelta(days=30)
    recent_exams = Exams.objects.filter(
        created_at__gte=recent_date
    ).order_by('-created_at')[:5]  # Get last 10 recent exams
    
    profile = Profile.objects.get(user=request.user)
    
    context = {
        'recent_exams': recent_exams,
        'profile': profile,
    }
    return render(request, 'exams/recent_exams.html', context)

def get_grade(score, exam):
    interval = GradingInterval.objects.filter(
        exam=exam,
        min_score__lte=score,
        max_score__gte=score
    ).first()
    return interval if interval else None

@login_required
def exam_result(request, exam_id):
    exam = get_object_or_404(Exams, id=exam_id)
    
    try:
        # Get the most recent result for this exam and user
        result = Result.objects.filter(
            user=request.user,
            exam=exam
        ).latest('created_at')  # Make sure you have created_at field in Result model
    except Result.DoesNotExist:
        messages.error(request, 'No result found for this exam.')
        return redirect('exam_list')
    
    questions = Question.objects.filter(exam=exam)
    responses = []
    correct_answers = 0
    
    for question in questions:
        try:
            response = UserResponse.objects.filter(
                question=question,
                user=request.user
            ).latest('created_at')
            
            is_correct = response.selected_option.strip().lower() == question.correct_answer.strip().lower()
            if is_correct:
                correct_answers += 1
            
            responses.append({
                'question': question,
                'selected_option': response.selected_option,
                'correct_answer': question.correct_answer,
                'is_correct': is_correct
            })
        except UserResponse.DoesNotExist:
            continue

    total_questions = questions.count()
    score = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    passed = score >= exam.passing_percentage

    # Get grade based on score
    grade_interval = get_grade(score, exam)
    
    context = {
        'exam': exam,
        'result': result,
        'responses': responses,
        'total_questions': total_questions,
        'correct_answers': correct_answers,
        'score': round(score, 2),
        'passed': passed,
        'grade': grade_interval.grade if grade_interval else None,
        'grade_description': grade_interval.description if grade_interval else None,
    }
    
    return render(request, 'exam_results.html', context)

@login_required
def performance_view(request):
    exam = Exams.objects.all()
    profile = Profile.objects.get(user=request.user)
    # Get all results for the current user
    user_results = Result.objects.filter(user=request.user).select_related('exam')
    
    # Overall statistics
    total_exams = user_results.count()
    exams_passed = user_results.filter(score__gte=F('exam__passing_percentage')).count()
    average_score = user_results.aggregate(Avg('score'))['score__avg'] or 0
    
    # Recent exam performance (last 5 exams)
    recent_results = user_results.order_by('-id')[:5]
    
    # Performance by exam type (premium vs free)
    premium_performance = {
        'total_exams': user_results.filter(exam__is_premium=True).count(),
        'average_score': user_results.filter(exam__is_premium=True).aggregate(Avg('score'))['score__avg'] or 0,
        'highest_score': user_results.filter(exam__is_premium=True).aggregate(Max('score'))['score__max'] or 0,
    }
    
    free_performance = {
        'total_exams': user_results.filter(exam__is_premium=False).count(),
        'average_score': user_results.filter(exam__is_premium=False).aggregate(Avg('score'))['score__avg'] or 0,
        'highest_score': user_results.filter(exam__is_premium=False).aggregate(Max('score'))['score__max'] or 0,
    }

    context = {
        'total_exams': total_exams,
        'exams_passed': exams_passed,
        'average_score': average_score,
        'recent_results': recent_results,
        'premium_performance': premium_performance,
        'free_performance': free_performance,
        'exam': exam,
        'profile': profile,
    }
    
    return render(request, 'performance.html', context)


from django.urls import path
from .views import payment_view, take_exam, exam_results, exam_questions, exam_list, exam_detail, student_dashboard,  view_results, student_analytics, subscription_plans, initialize_payment, verify_payment, payment_success, subscription_status, recent_exams, exam_result
from .views import performance_view

urlpatterns = [
    # path('dashboard/', teacher_dashboard, name='teacher_dashboard'),
    # path('create_exam/', create_exam, name='create_exam'),
    # path('teacher/', teacher_dashboard, name='teacher_dashboard'),
    path('student/', student_dashboard, name='student_dashboard'),
    # path('create-question/', create_question, name='create_question'),
    path('view-results/<int:exam_id>/', view_results, name='view_results'),
    path('analytics/', student_analytics, name='student_analytics'),
    # path('create_exam/', create_exam, name='create_exam'),
    # path('create_question/', create_question, name='create_question'),
    path('exam/<int:exam_id>/', exam_detail, name='exam_detail'),
    path('take_exam/<int:exam_id>/', take_exam, name='take_exam'),
    path('exam_list/', exam_list, name='exam_list'),
    path('exam/<int:exam_id>/questions/', exam_questions, name='exam_questions'),
    # path('exam/<int:exam_id>/take/<int:question_index>/', take_exam, name='take_exam'),
    # path('exam/<int:exam_id>/results/', exam_results, name='exam_results'),
    path('payment/<int:exam_id>/', payment_view, name='pay_exam'),
    path('subscription/plans/', subscription_plans, name='subscription_plans'),
    path('payment/initialize/', initialize_payment, name='initialize_payment'),
    path('payment/verify/<str:tx_ref>/', verify_payment, name='verify_payment'),
    path('payment/success/', payment_success, name='payment_success'),
    path('subscription/status/', subscription_status, name='subscription_status'),
    path('recent-exams/', recent_exams, name='recent_exams'),
    path('exam/<int:exam_id>/result/', exam_result, name='exam_result'),
    path('performance/', performance_view, name='performance'),
]
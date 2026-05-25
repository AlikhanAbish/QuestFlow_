from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.TaskListView.as_view(), name='task_list'),
    path('kanban/', views.TaskKanbanView.as_view(), name='task_kanban'),
    path('create/', views.TaskCreateView.as_view(), name='task_create'),
    path('<int:pk>/', views.TaskDetailView.as_view(), name='task_detail'),
    path('<int:pk>/update/', views.TaskUpdateView.as_view(), name='task_update'),
    path('<int:pk>/delete/', views.TaskDeleteView.as_view(), name='task_delete'),
    path('<int:pk>/status/', views.TaskStatusUpdateView.as_view(), name='task_status_update'),
    path('<int:pk>/comment/', views.TaskCommentView.as_view(), name='task_comment'),
    path('<int:pk>/comments/', views.TaskCommentsPartialView.as_view(), name='task_comments_partial'),
    path('export/csv/', views.TaskExportCSVView.as_view(), name='task_export_csv'),
    path('filter/partial/', views.TaskFilterPartialView.as_view(), name='task_filter_partial'),
]

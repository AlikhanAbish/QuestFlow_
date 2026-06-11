from django.test import TestCase
from django.contrib.auth import get_user_model
from apps.gamification.models import UserLevel, GamificationRule
from apps.gamification.engine import GamificationEngine
from apps.tasks.models import Task, TaskStatus
from apps.tasks.services import TaskService
from apps.companies.models import Company

User = get_user_model()


class XPAwardTest(TestCase):
    def setUp(self):
        """Create test data."""
        self.company = Company.objects.create(name="Test Company")
        self.user = User.objects.create_user(
            username="employee_test",
            email="employee@example.com",
            password="testpass123",
            first_name="Test",
            last_name="User",
            role="employee",
            company=self.company
        )
        self.manager = User.objects.create_user(
            username="manager_test",
            email="manager@example.com",
            password="testpass123",
            role="manager",
            company=self.company
        )

    def test_xp_awarded_on_task_completion(self):
        """Test that XP is awarded when a task is marked as done."""
        task = Task.objects.create(
            company=self.company,
            created_by=self.manager,
            assigned_to=self.user,
            title="Test Task",
            description="Test task for XP",
            status=TaskStatus.TODO
        )
        
        # Get initial XP
        user_level = UserLevel.objects.get(user=self.user)
        initial_xp = user_level.total_xp
        
        # Mark task as done
        TaskService.change_task_status(task, self.manager, TaskStatus.DONE)
        
        # Check XP was awarded
        user_level.refresh_from_db()
        expected_xp = initial_xp + 100  # task_done rule gives 100 XP
        self.assertEqual(user_level.total_xp, expected_xp)

    def test_engine_award_xp_with_rule(self):
        """Test that GamificationEngine correctly awards XP when rule exists."""
        engine = GamificationEngine(self.user)
        user_level = UserLevel.objects.get(user=self.user)
        initial_xp = user_level.total_xp
        
        # Award XP
        txn, _ = engine.award_xp(action='task_done', note='Test award')
        
        # Check that transaction was created and XP was awarded
        self.assertIsNotNone(txn)
        self.assertEqual(txn.amount, 100)
        
        user_level.refresh_from_db()
        self.assertEqual(user_level.total_xp, initial_xp + 100)

    def test_engine_ignores_missing_rule(self):
        """Test that GamificationEngine returns None when rule doesn't exist."""
        engine = GamificationEngine(self.user)
        user_level = UserLevel.objects.get(user=self.user)
        initial_xp = user_level.total_xp
        
        # Try to award XP for non-existent action
        txn, _ = engine.award_xp(action='nonexistent_action')
        
        # Check that no transaction was created
        self.assertIsNone(txn)
        
        user_level.refresh_from_db()
        self.assertEqual(user_level.total_xp, initial_xp)

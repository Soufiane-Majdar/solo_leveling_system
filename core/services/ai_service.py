from django.utils import timezone
from datetime import timedelta
import random

class AIService:
    """Service for AI-powered quest and goal generation"""
    
    def __init__(self):
        self.quest_templates = {
            'PRODUCTIVITY': [
                {
                    'title': 'Complete {task_count} tasks',
                    'description': 'Focus on completing {task_count} tasks to make progress on your goal.',
                    'difficulties': {
                        1: {'task_count': '2-3', 'xp': 100, 'coins': 10},
                        2: {'task_count': '4-5', 'xp': 200, 'coins': 20},
                        3: {'task_count': '6-8', 'xp': 300, 'coins': 30},
                    }
                },
                {
                    'title': 'Work on {activity} for {time_amount}',
                    'description': 'Spend focused time on your goal without distractions.',
                    'difficulties': {
                        1: {'time_amount': '30 minutes', 'xp': 100, 'coins': 10},
                        2: {'time_amount': '1 hour', 'xp': 200, 'coins': 20},
                        3: {'time_amount': '2 hours', 'xp': 300, 'coins': 30},
                    }
                }
            ],
            'LEARNING': [
                {
                    'title': 'Study session: {duration}',
                    'description': 'Focus on learning and practicing your subject.',
                    'difficulties': {
                        1: {'duration': '30 minutes', 'xp': 100, 'coins': 10},
                        2: {'duration': '1 hour', 'xp': 200, 'coins': 20},
                        3: {'duration': '2 hours', 'xp': 400, 'coins': 40},
                    }
                },
                {
                    'title': 'Practice session: {count} exercises',
                    'description': 'Complete practice exercises to reinforce your knowledge.',
                    'difficulties': {
                        1: {'count': '3-5', 'xp': 150, 'coins': 15},
                        2: {'count': '6-8', 'xp': 300, 'coins': 30},
                        3: {'count': '9-12', 'xp': 450, 'coins': 45},
                    }
                }
            ],
            'FITNESS': [
                {
                    'title': 'Workout session: {duration}',
                    'description': 'Complete a {intensity} workout session.',
                    'difficulties': {
                        1: {'duration': '20 minutes', 'intensity': 'light', 'xp': 100, 'coins': 10},
                        2: {'duration': '40 minutes', 'intensity': 'moderate', 'xp': 200, 'coins': 20},
                        3: {'duration': '60 minutes', 'intensity': 'intense', 'xp': 300, 'coins': 30},
                    }
                },
                {
                    'title': 'Exercise goal: {target}',
                    'description': 'Push yourself to reach your fitness milestone.',
                    'difficulties': {
                        1: {'target': '2000 steps', 'xp': 100, 'coins': 10},
                        2: {'target': '5000 steps', 'xp': 200, 'coins': 20},
                        3: {'target': '10000 steps', 'xp': 300, 'coins': 30},
                    }
                }
            ]
        }
    
    def generate_quest_suggestions(self, user_profile, goal=None):
        """Generate quest suggestions based on user profile and optional goal"""
        suggestions = []
        
        # Determine categories to generate suggestions from
        if goal:
            categories = [self._determine_goal_category(goal.title, goal.description)]
        else:
            categories = list(self.quest_templates.keys())
        
        # Generate 3-5 suggestions per category
        for category in categories:
            templates = self.quest_templates.get(category, [])
            num_suggestions = min(len(templates), random.randint(2, 3))
            
            for _ in range(num_suggestions):
                template = random.choice(templates)
                difficulty = random.randint(1, min(3, user_profile.level))
                
                quest_data = self._generate_quest_from_template(
                    template,
                    difficulty,
                    goal.title if goal else "",
                    goal.description if goal else ""
                )
                
                # Add category context
                quest_data['category'] = category
                suggestions.append(quest_data)
        
        return suggestions
    
    def generate_quests_from_goal(self, user_profile, goal):
        """Generate a set of specific quests to help achieve the goal"""
        category = self._determine_goal_category(goal.title, goal.description)
        templates = self.quest_templates.get(category, self.quest_templates['PRODUCTIVITY'])
        
        quests = []
        num_quests = random.randint(3, 5)  # Generate 3-5 quests per goal
        
        for _ in range(num_quests):
            template = random.choice(templates)
            difficulty = random.randint(1, min(3, user_profile.level))  # Cap difficulty by user level
            
            quest_data = self._generate_quest_from_template(
                template, 
                difficulty,
                goal.title,
                goal.description
            )
            
            # Add deadline based on goal deadline if exists
            if goal.deadline:
                days_until_deadline = (goal.deadline - timezone.now()).days
                if days_until_deadline > 0:
                    quest_data['deadline'] = timezone.now() + timedelta(
                        days=random.randint(1, max(days_until_deadline, 1))
                    )
            
            quests.append(quest_data)
        
        return quests
    
    def _determine_goal_category(self, title, description):
        """Determine the most appropriate category for the goal"""
        title_desc = (title + " " + description).upper()
        
        if any(word in title_desc for word in ['STUDY', 'LEARN', 'COURSE', 'EDUCATION']):
            return 'LEARNING'
        elif any(word in title_desc for word in ['EXERCISE', 'WORKOUT', 'FITNESS', 'GYM']):
            return 'FITNESS'
        else:
            return 'PRODUCTIVITY'
    
    def _generate_quest_from_template(self, template, difficulty, goal_title, goal_description):
        """Generate a specific quest from a template"""
        difficulty_data = template['difficulties'][difficulty]
        
        # Extract key terms from goal
        keywords = self._extract_keywords(goal_title, goal_description)
        
        # Create format dictionary with all possible variables
        format_dict = {
            # Template-specific variables
            'task_count': difficulty_data.get('task_count', '3'),
            'time_amount': difficulty_data.get('time_amount', '30 minutes'),
            'duration': difficulty_data.get('duration', '30 minutes'),
            'count': difficulty_data.get('count', '3'),
            'intensity': difficulty_data.get('intensity', 'moderate'),
            'target': difficulty_data.get('target', '2000 steps'),
            
            # Extracted keywords
            'activity': keywords.get('activity', 'the task'),
            'subject': keywords.get('subject', 'your subject'),
            'topic': keywords.get('subject', 'the material'),
        }
        
        # Generate quest details
        quest_details = {
            'title': template['title'].format(**format_dict),
            'description': template['description'].format(**format_dict),
            'difficulty': difficulty,
            'reward_xp': difficulty_data['xp'],
            'reward_coins': difficulty_data['coins'],
            'required_level': max(1, difficulty - 1),  # Higher difficulty quests require higher levels
        }
        
        return quest_details
    
    def _extract_keywords(self, title, description):
        """Extract relevant keywords from goal title and description"""
        text = (title + " " + description).lower()
        
        # Extract activity type
        activities = ['reading', 'writing', 'coding', 'studying', 'exercise', 
                     'meditation', 'practice', 'training', 'work']
        activity = next((word for word in activities if word in text), None)
        
        # Extract subject matter
        subjects = ['math', 'science', 'history', 'programming', 'language',
                   'project', 'presentation', 'report', 'analysis']
        subject = next((word for word in subjects if word in text), None)
        
        return {
            'activity': activity,
            'subject': subject,
        }

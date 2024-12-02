from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Sum
import requests
import json
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage

from .models import UserProfile, Quest, Goal, Achievement, CommunityPost, UserQuest
from .forms import (
    UserRegistrationForm, UserProfileForm, QuestForm,
    GoalForm, CommunityPostForm, UserSettingsForm, UserProfileSettingsForm, 
    UserProfileEditForm, CommentForm, ContactForm
)
from .services.ai_service import AIService

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return render(request, 'core/home.html')

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        
        if form.is_valid() and profile_form.is_valid():
            user = form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            
            login(request, user)
            messages.success(request, 'Welcome to Solo Leveling System!')
            return redirect('personality_quiz')
    else:
        form = UserRegistrationForm()
        profile_form = UserProfileForm()
    
    return render(request, 'core/register.html', {
        'form': form,
        'profile_form': profile_form
    })

@login_required
def personality_quiz(request):
    if request.method == 'POST':
        # Process personality quiz answers
        answers = request.POST.dict()
        personality_result = analyze_personality(answers)
        
        # Update user profile with personality traits
        profile = request.user.userprofile
        profile.personality_type = personality_result['type']
        profile.strengths = personality_result['strengths']
        profile.weaknesses = personality_result['weaknesses']
        profile.save()
        
        messages.success(request, f'Your personality type: {personality_result["type"]}')
        return redirect('dashboard')
    
    return render(request, 'core/personality_quiz.html')

@login_required
def dashboard(request):
    user_profile = request.user.userprofile
    
    # Get user's goals and quests
    goals = Goal.objects.filter(
        user=request.user,
        is_active=True
    ).order_by('-priority', '-created_at')
    
    active_quests = Quest.objects.filter(
        user=request.user, 
        status='in_progress'
    ).select_related('goal').order_by('-created_at')[:5]
    
    completed_quests = Quest.objects.filter(
        user=request.user, 
        status='completed',
        completed_at__isnull=False
    ).select_related('goal').order_by('-updated_at')[:5]
    
    # Calculate statistics
    total_quests = Quest.objects.filter(user=request.user).count()
    completed_quest_count = Quest.objects.filter(user=request.user, status='completed').count()
    completion_rate = (completed_quest_count / total_quests * 100) if total_quests > 0 else 0
    
    # Get active goals with progress
    active_goals = goals.filter(
        is_active=True
    ).exclude(
        deadline__lt=timezone.now()
    ).order_by('-priority', '-created_at')[:5]
    
    context = {
        'user_profile': user_profile,
        'active_quests': active_quests,
        'completed_quests': completed_quests,
        'active_goals': active_goals,
        'total_quests': total_quests,
        'completed_quest_count': completed_quest_count,
        'completion_rate': round(completion_rate, 1),
        'xp_to_next_level': user_profile.xp_to_next_level(),
    }
    
    return render(request, 'core/dashboard.html', context)

@login_required
def quest_list(request):
    # Start with all quests for the user
    quests = Quest.objects.filter(user=request.user)
    
    # Get all active goals for the filter dropdown
    goals = Goal.objects.filter(user=request.user, is_active=True)
    
    # Apply filters
    status = request.GET.get('status')
    if status:
        quests = quests.filter(status=status)
    
    difficulty = request.GET.get('difficulty')
    if difficulty:
        quests = quests.filter(difficulty=int(difficulty))
    
    goal_id = request.GET.get('goal')
    if goal_id:
        quests = quests.filter(goal_id=goal_id)
    
    search = request.GET.get('search')
    if search:
        quests = quests.filter(title__icontains=search) | quests.filter(description__icontains=search)
    
    # Order quests
    quests = quests.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(quests, 9)  # Show 9 quests per page
    page = request.GET.get('page')
    try:
        quests = paginator.page(page)
    except PageNotAnInteger:
        quests = paginator.page(1)
    except EmptyPage:
        quests = paginator.page(paginator.num_pages)
    
    context = {
        'quests': quests,
        'goals': goals,
        'is_paginated': True if paginator.num_pages > 1 else False,
        'page_obj': quests,
        'now': timezone.now(),  # Add current time for deadline comparison
    }
    
    return render(request, 'core/quest_list.html', context)

@login_required
def quest_create(request):
    goal_id = request.GET.get('goal')
    goal = None
    if goal_id:
        goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    
    if request.method == 'POST':
        form = QuestForm(request.POST, user=request.user)
        if form.is_valid():
            quest = form.save(commit=False)
            quest.user = request.user
            if goal:
                quest.goal = goal
            quest.save()
            
            messages.success(request, 'Quest created successfully!')
            if goal:
                return redirect('goal_detail', goal_id=goal.id)
            return redirect('quest_list')
    else:
        initial_data = {}
        if goal:
            initial_data['goal'] = goal
        form = QuestForm(initial=initial_data, user=request.user)
        
        # Get AI suggestions
        ai_service = AIService()
        try:
            suggestions = ai_service.generate_quest_suggestions(request.user.userprofile, goal)
        except Exception as e:
            print(f"Error generating suggestions: {str(e)}")  # Add debug logging
            suggestions = []
            messages.warning(request, 'Could not generate quest suggestions at this time.')
    
    context = {
        'form': form,
        'suggestions': suggestions if 'suggestions' in locals() else [],
        'goal': goal
    }
    return render(request, 'core/quest_form.html', context)

@login_required
def quest_complete(request, quest_id):
    quest = get_object_or_404(Quest, id=quest_id, user=request.user)
    
    if quest.status != 'completed':
        quest.complete()
        messages.success(request, f'Quest completed! Earned {quest.reward_xp * quest.difficulty} XP and {quest.reward_coins * quest.difficulty} coins!')
    
    return redirect('dashboard')

@login_required
def quest_fail(request, quest_id):
    quest = get_object_or_404(Quest, id=quest_id, user=request.user)
    
    if quest.status != 'failed':
        quest.fail()
        messages.warning(request, 'Quest failed. Better luck next time!')
    
    return redirect('dashboard')

@login_required
def quest_start(request, quest_id):
    quest = get_object_or_404(Quest, id=quest_id, user=request.user)
    
    if quest.status == 'not_started':
        quest.start()
        messages.info(request, f'Started quest: {quest.title}')
    
    return redirect('dashboard')

@login_required
def goal_list(request):
    goals = Goal.objects.filter(user=request.user).order_by('deadline')
    return render(request, 'core/goal_list.html', {'goals': goals})

@login_required
def goal_create(request):
    if request.method == 'POST':
        form = GoalForm(request.POST)
        if form.is_valid():
            try:
                goal = form.save(commit=False)
                goal.user = request.user
                goal.save()
                
                # Generate quests for this goal
                ai_service = AIService()
                quests = ai_service.generate_quests_from_goal(request.user.userprofile, goal)
                
                # Create the quests
                created_quests = []
                for quest_data in quests:
                    try:
                        quest = Quest.objects.create(
                            user=request.user,
                            goal=goal,  # Link quest to goal
                            title=quest_data['title'],
                            description=quest_data['description'],
                            difficulty=int(quest_data['difficulty']),  # Ensure difficulty is an integer
                            reward_xp=quest_data['reward_xp'],
                            reward_coins=quest_data['reward_coins'],
                            required_level=quest_data['required_level'],
                            deadline=quest_data.get('deadline')
                        )
                        created_quests.append(quest)
                    except (ValueError, TypeError) as e:
                        # Log the error but continue with other quests
                        print(f"Error creating quest: {str(e)}")
                        continue
                
                if created_quests:
                    messages.success(request, f'Goal created with {len(created_quests)} auto-generated quests to help you achieve it!')
                else:
                    messages.warning(request, 'Goal created but there was an issue generating quests. Please try creating quests manually.')
                
                return redirect('quest_list')
            except Exception as e:
                messages.error(request, f'Error creating goal: {str(e)}')
                return render(request, 'core/goal_form.html', {'form': form})
    else:
        form = GoalForm()
    
    return render(request, 'core/goal_form.html', {'form': form})

@login_required
def goal_detail(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    quests = Quest.objects.filter(user=request.user, goal=goal).order_by('-created_at')
    
    context = {
        'goal': goal,
        'quests': quests,
        'completed_quests': goal.completed_quests_count,
        'active_quests': goal.active_quests_count,
        'total_quests': goal.total_quests_count,
        'completion_percentage': goal.completion_percentage
    }
    
    return render(request, 'core/goal_detail.html', context)

@login_required
def community_feed(request):
    posts = CommunityPost.objects.all().order_by('-created_at')
    return render(request, 'core/community.html', {'posts': posts})

@login_required
def post_create(request):
    if request.method == 'POST':
        form = CommunityPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.user = request.user
            post.save()
            
            messages.success(request, 'Post created successfully!')
            return redirect('community_feed')
    else:
        form = CommunityPostForm()
    
    return render(request, 'core/post_form.html', {'form': form})

@login_required
def profile(request):
    user_profile = request.user.userprofile
    completed_quests = Quest.objects.filter(user=request.user, status='COMPLETED').count()
    active_quests = Quest.objects.filter(user=request.user, status='IN_PROGRESS').count()
    total_xp = user_profile.experience + (user_profile.level - 1) * 100
    
    context = {
        'user_profile': user_profile,
        'completed_quests': completed_quests,
        'active_quests': active_quests,
        'total_xp': total_xp,
    }
    return render(request, 'core/profile.html', context)

@login_required
def settings(request):
    if request.method == 'POST':
        form = UserSettingsForm(request.POST, instance=request.user)
        profile_form = UserProfileSettingsForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid() and profile_form.is_valid():
            form.save()
            profile_form.save()
            messages.success(request, 'Your settings have been updated successfully!')
            return redirect('profile')
    else:
        form = UserSettingsForm(instance=request.user)
        profile_form = UserProfileSettingsForm(instance=request.user.userprofile)
    
    context = {
        'form': form,
        'profile_form': profile_form,
    }
    return render(request, 'core/settings.html', context)

@login_required
def profile_edit(request):
    if request.method == 'POST':
        form = UserProfileEditForm(request.POST, request.FILES, instance=request.user.userprofile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated successfully!')
            return redirect('profile')
    else:
        form = UserProfileEditForm(instance=request.user.userprofile)
    
    context = {
        'form': form,
    }
    return render(request, 'core/profile_edit.html', context)

@login_required
def goal_edit(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == 'POST':
        form = GoalForm(request.POST, instance=goal)
        if form.is_valid():
            form.save()
            messages.success(request, 'Goal updated successfully!')
            return redirect('goal_list')
    else:
        form = GoalForm(instance=goal)
    
    context = {
        'form': form,
        'goal': goal,
    }
    return render(request, 'core/goal_form.html', context)

@login_required
def goal_delete(request, goal_id):
    goal = get_object_or_404(Goal, id=goal_id, user=request.user)
    if request.method == 'POST':
        goal.delete()
        messages.success(request, 'Goal deleted successfully!')
        return redirect('goal_list')
    
    context = {
        'goal': goal,
    }
    return render(request, 'core/goal_confirm_delete.html', context)

@login_required
def post_detail(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id)
    comments = post.comments.all().order_by('-created_at')
    
    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.user = request.user
            comment.post = post
            comment.save()
            messages.success(request, 'Comment added successfully!')
            return redirect('post_detail', post_id=post.id)
    else:
        comment_form = CommentForm()
    
    context = {
        'post': post,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'core/post_detail.html', context)

@login_required
def post_edit(request, post_id):
    post = get_object_or_404(CommunityPost, id=post_id, user=request.user)
    if request.method == 'POST':
        form = CommunityPostForm(request.POST, instance=post)
        if form.is_valid():
            form.save()
            messages.success(request, 'Post updated successfully!')
            return redirect('post_detail', post_id=post.id)
    else:
        form = CommunityPostForm(instance=post)
    
    context = {
        'form': form,
        'post': post,
    }
    return render(request, 'core/post_form.html', context)

def about(request):
    return render(request, 'core/about.html')

def privacy(request):
    return render(request, 'core/privacy.html')

def terms(request):
    return render(request, 'core/terms.html')

def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            # Process the form data (send email, save to database, etc.)
            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')
    else:
        form = ContactForm()
    
    context = {
        'form': form,
    }
    return render(request, 'core/contact.html', context)

# Helper Functions
def analyze_personality(answers):
    """
    Analyze quiz answers using a free personality analysis API
    Returns personality type and traits
    """
    # Example using a mock API (replace with actual free API)
    personality_types = {
        'achiever': {
            'strengths': ['goal-oriented', 'persistent', 'organized'],
            'weaknesses': ['perfectionist', 'workaholic']
        },
        'explorer': {
            'strengths': ['creative', 'adaptable', 'curious'],
            'weaknesses': ['unfocused', 'restless']
        },
        'socializer': {
            'strengths': ['empathetic', 'collaborative', 'communicative'],
            'weaknesses': ['dependent', 'conflict-avoidant']
        },
        'competitor': {
            'strengths': ['driven', 'ambitious', 'focused'],
            'weaknesses': ['impatient', 'overly competitive']
        }
    }
    
    # Simple scoring system (replace with API call)
    scores = {
        'achiever': 0,
        'explorer': 0,
        'socializer': 0,
        'competitor': 0
    }
    
    for answer in answers.values():
        if isinstance(answer, str):
            for ptype in scores:
                if ptype in answer.lower():
                    scores[ptype] += 1
    
    personality_type = max(scores, key=scores.get)
    traits = personality_types[personality_type]
    
    return {
        'type': personality_type,
        'strengths': traits['strengths'],
        'weaknesses': traits['weaknesses']
    }

def generate_goal_tasks(goal):
    """
    Generate tasks for a goal using AI recommendations
    """
    try:
        # Example task generation (replace with actual AI API call)
        default_tasks = [
            {
                'name': f'Plan {goal.title}',
                'description': 'Create a detailed plan with milestones',
                'difficulty': 'E',
                'duration_hours': 1
            },
            {
                'name': f'Research {goal.title}',
                'description': 'Gather necessary information and resources',
                'difficulty': 'D',
                'duration_hours': 2
            },
            {
                'name': f'Execute {goal.title} - Phase 1',
                'description': 'Begin implementation of the plan',
                'difficulty': 'C',
                'duration_hours': 4
            }
        ]
        
        for task in default_tasks:
            Quest.objects.create(
                user=goal.user,
                name=task['name'],
                description=task['description'],
                difficulty=task['difficulty'],
                duration_hours=task['duration_hours']
            )
            
    except Exception as e:
        print(f"Error generating tasks: {e}")

def check_quest_achievements(user):
    """
    Check and award achievements based on quest completion
    """
    completed_quests = UserQuest.objects.filter(
        user=user,
        completed=True
    ).count()
    
    # Achievement thresholds
    achievement_levels = {
        10: 'Novice Hunter',
        50: 'Expert Hunter',
        100: 'Master Hunter',
        500: 'Shadow Monarch'
    }
    
    for threshold, title in achievement_levels.items():
        if completed_quests >= threshold:
            Achievement.objects.get_or_create(
                user=user,
                name=title,
                defaults={
                    'description': f'Completed {threshold} quests',
                    'xp_reward': threshold * 10,
                    'coin_reward': threshold * 5
                }
            )
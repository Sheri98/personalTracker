#!/usr/bin/env python3
"""
Personal Task Tracker - A comprehensive task management application
Features:
- Task management with priorities and categories
- Calendar-based date selection
- Progress tracking
- Backtrack/Ideas dump
- Statistics dashboard
- Data persistence
- Search and filtering
- Export functionality
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import json
import os
import uuid
from typing import Optional, Dict, List, Any
import csv


# ============================================================================
# Data Models and Storage
# ============================================================================

class DataManager:
    """Handles data persistence using JSON files"""

    def __init__(self, data_file: str = "tracker_data.json"):
        self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return self._get_default_data()
        return self._get_default_data()

    def _get_default_data(self) -> Dict[str, Any]:
        """Return default data structure"""
        return {
            "tasks": [],
            "backtrack": [],
            "completed_history": [],
            "settings": {
                "theme": "light",
                "default_view": "all"
            },
            "streaks": {},
            "statistics": {
                "total_completed": 0,
                "total_created": 0
            }
        }

    def save_data(self) -> None:
        """Save data to JSON file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except IOError as e:
            messagebox.showerror("Error", f"Failed to save data: {e}")

    def add_task(self, task: Dict) -> None:
        """Add a new task"""
        task['id'] = str(uuid.uuid4())
        task['created_at'] = datetime.now().isoformat()
        task['updated_at'] = datetime.now().isoformat()
        self.data['tasks'].append(task)
        self.data['statistics']['total_created'] += 1
        self.save_data()

    def update_task(self, task_id: str, updates: Dict) -> None:
        """Update an existing task"""
        for task in self.data['tasks']:
            if task['id'] == task_id:
                task.update(updates)
                task['updated_at'] = datetime.now().isoformat()
                break
        self.save_data()

    def delete_task(self, task_id: str) -> None:
        """Delete a task"""
        self.data['tasks'] = [t for t in self.data['tasks'] if t['id'] != task_id]
        self.save_data()

    def complete_task(self, task_id: str) -> None:
        """Mark task as complete and move to history"""
        for task in self.data['tasks']:
            if task['id'] == task_id:
                task['status'] = 'completed'
                task['completed_at'] = datetime.now().isoformat()
                self.data['completed_history'].append(task.copy())
                self.data['statistics']['total_completed'] += 1
                self._update_streak(task.get('classification', ''))
                break
        self.data['tasks'] = [t for t in self.data['tasks'] if t['id'] != task_id]
        self.save_data()

    def _update_streak(self, classification: str) -> None:
        """Update streak for a classification"""
        today = datetime.now().strftime("%Y-%m-%d")
        if classification not in self.data['streaks']:
            self.data['streaks'][classification] = {
                'current': 1,
                'best': 1,
                'last_date': today
            }
        else:
            streak = self.data['streaks'][classification]
            last_date = datetime.strptime(streak['last_date'], "%Y-%m-%d")
            today_date = datetime.strptime(today, "%Y-%m-%d")
            diff = (today_date - last_date).days

            if diff == 1:
                streak['current'] += 1
            elif diff > 1:
                streak['current'] = 1

            streak['best'] = max(streak['best'], streak['current'])
            streak['last_date'] = today

    def add_backtrack(self, idea: Dict) -> None:
        """Add an idea to backtrack"""
        idea['id'] = str(uuid.uuid4())
        idea['created_at'] = datetime.now().isoformat()
        self.data['backtrack'].append(idea)
        self.save_data()

    def delete_backtrack(self, idea_id: str) -> None:
        """Delete an idea from backtrack"""
        self.data['backtrack'] = [b for b in self.data['backtrack'] if b['id'] != idea_id]
        self.save_data()

    def promote_backtrack(self, idea_id: str) -> Optional[Dict]:
        """Promote a backtrack idea to a task"""
        for idea in self.data['backtrack']:
            if idea['id'] == idea_id:
                self.data['backtrack'].remove(idea)
                self.save_data()
                return idea
        return None

    def get_tasks(self, filters: Optional[Dict] = None) -> List[Dict]:
        """Get tasks with optional filtering"""
        tasks = self.data['tasks']
        if filters:
            if filters.get('classification'):
                tasks = [t for t in tasks if t.get('classification') == filters['classification']]
            if filters.get('importance'):
                tasks = [t for t in tasks if t.get('importance') == filters['importance']]
            if filters.get('status'):
                tasks = [t for t in tasks if t.get('status') == filters['status']]
            if filters.get('search'):
                search = filters['search'].lower()
                tasks = [t for t in tasks if search in t.get('name', '').lower() or
                        search in t.get('notes', '').lower()]
        return tasks

    def get_backtrack(self) -> List[Dict]:
        """Get all backtrack ideas"""
        return self.data['backtrack']

    def get_statistics(self) -> Dict:
        """Get statistics"""
        stats = self.data['statistics'].copy()
        stats['active_tasks'] = len(self.data['tasks'])
        stats['backtrack_ideas'] = len(self.data['backtrack'])
        stats['streaks'] = self.data['streaks']

        # Count by importance
        stats['by_importance'] = {}
        for task in self.data['tasks']:
            imp = task.get('importance', 'Medium')
            stats['by_importance'][imp] = stats['by_importance'].get(imp, 0) + 1

        # Count by classification
        stats['by_classification'] = {}
        for task in self.data['tasks']:
            cls = task.get('classification', 'Other')
            stats['by_classification'][cls] = stats['by_classification'].get(cls, 0) + 1

        # Tasks due today/overdue
        today = datetime.now().date()
        stats['due_today'] = 0
        stats['overdue'] = 0
        for task in self.data['tasks']:
            if task.get('due_date') and task.get('due_type') == 'specific':
                try:
                    due = datetime.fromisoformat(task['due_date']).date()
                    if due == today:
                        stats['due_today'] += 1
                    elif due < today:
                        stats['overdue'] += 1
                except (ValueError, TypeError):
                    pass

        return stats

    def export_to_csv(self, filename: str) -> None:
        """Export tasks to CSV"""
        with open(filename, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Name', 'Classification', 'Importance', 'Due Type',
                           'Due Date', 'Progress', 'Notes', 'Created At'])
            for task in self.data['tasks']:
                writer.writerow([
                    task.get('name', ''),
                    task.get('classification', ''),
                    task.get('importance', ''),
                    task.get('due_type', ''),
                    task.get('due_date', ''),
                    task.get('progress', 0),
                    task.get('notes', ''),
                    task.get('created_at', '')
                ])


# ============================================================================
# Custom Widgets
# ============================================================================

class DateTimePicker(tk.Toplevel):
    """Custom date and time picker dialog"""

    def __init__(self, parent, initial_date=None):
        super().__init__(parent)
        self.title("Select Date & Time")
        self.geometry("300x350")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.result = None
        self.current_date = initial_date or datetime.now()
        self.selected_date = self.current_date.date()

        self._create_widgets()
        self._update_calendar()

        # Center the dialog
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

    def _create_widgets(self):
        # Month/Year navigation
        nav_frame = ttk.Frame(self)
        nav_frame.pack(fill='x', padx=10, pady=5)

        ttk.Button(nav_frame, text="<", width=3,
                  command=self._prev_month).pack(side='left')

        self.month_year_label = ttk.Label(nav_frame, text="", font=('Arial', 11, 'bold'))
        self.month_year_label.pack(side='left', expand=True)

        ttk.Button(nav_frame, text=">", width=3,
                  command=self._next_month).pack(side='right')

        # Calendar grid
        self.cal_frame = ttk.Frame(self)
        self.cal_frame.pack(fill='both', expand=True, padx=10)

        # Day headers
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        for i, day in enumerate(days):
            ttk.Label(self.cal_frame, text=day, width=4,
                     font=('Arial', 9, 'bold')).grid(row=0, column=i, pady=2)

        # Day buttons
        self.day_buttons = []
        for row in range(6):
            row_buttons = []
            for col in range(7):
                btn = tk.Button(self.cal_frame, text="", width=4, height=1,
                              relief='flat', bd=1)
                btn.grid(row=row+1, column=col, padx=1, pady=1)
                row_buttons.append(btn)
            self.day_buttons.append(row_buttons)

        # Time selection
        time_frame = ttk.LabelFrame(self, text="Time (Optional)")
        time_frame.pack(fill='x', padx=10, pady=5)

        time_inner = ttk.Frame(time_frame)
        time_inner.pack(pady=5)

        self.hour_var = tk.StringVar(value="12")
        self.minute_var = tk.StringVar(value="00")

        ttk.Spinbox(time_inner, from_=0, to=23, width=3,
                   textvariable=self.hour_var, format="%02.0f").pack(side='left')
        ttk.Label(time_inner, text=":").pack(side='left')
        ttk.Spinbox(time_inner, from_=0, to=59, width=3,
                   textvariable=self.minute_var, format="%02.0f").pack(side='left')

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill='x', padx=10, pady=10)

        ttk.Button(btn_frame, text="Cancel",
                  command=self.destroy).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Select",
                  command=self._select).pack(side='right')
        ttk.Button(btn_frame, text="Today",
                  command=self._select_today).pack(side='left')

    def _update_calendar(self):
        """Update the calendar display"""
        self.month_year_label.config(
            text=self.current_date.strftime("%B %Y"))

        # Get first day of month and number of days
        first_day = self.current_date.replace(day=1)
        start_weekday = first_day.weekday()

        # Get number of days in month
        if self.current_date.month == 12:
            next_month = self.current_date.replace(year=self.current_date.year+1, month=1, day=1)
        else:
            next_month = self.current_date.replace(month=self.current_date.month+1, day=1)
        days_in_month = (next_month - first_day).days

        # Clear and update buttons
        day = 1
        for row in range(6):
            for col in range(7):
                btn = self.day_buttons[row][col]
                if row == 0 and col < start_weekday:
                    btn.config(text="", state='disabled', bg='#f0f0f0')
                elif day > days_in_month:
                    btn.config(text="", state='disabled', bg='#f0f0f0')
                else:
                    current_day = day
                    btn.config(text=str(day), state='normal',
                             command=lambda d=current_day: self._select_day(d))

                    # Highlight selected date
                    if (self.selected_date and
                        self.selected_date.year == self.current_date.year and
                        self.selected_date.month == self.current_date.month and
                        self.selected_date.day == day):
                        btn.config(bg='#4a90d9', fg='white')
                    # Highlight today
                    elif (datetime.now().date() ==
                          self.current_date.replace(day=day).date()):
                        btn.config(bg='#90EE90', fg='black')
                    else:
                        btn.config(bg='white', fg='black')
                    day += 1

    def _select_day(self, day):
        """Select a day"""
        self.selected_date = self.current_date.replace(day=day).date()
        self._update_calendar()

    def _prev_month(self):
        """Go to previous month"""
        if self.current_date.month == 1:
            self.current_date = self.current_date.replace(
                year=self.current_date.year-1, month=12)
        else:
            self.current_date = self.current_date.replace(
                month=self.current_date.month-1)
        self._update_calendar()

    def _next_month(self):
        """Go to next month"""
        if self.current_date.month == 12:
            self.current_date = self.current_date.replace(
                year=self.current_date.year+1, month=1)
        else:
            self.current_date = self.current_date.replace(
                month=self.current_date.month+1)
        self._update_calendar()

    def _select_today(self):
        """Select today's date"""
        self.current_date = datetime.now()
        self.selected_date = self.current_date.date()
        self._update_calendar()

    def _select(self):
        """Confirm selection"""
        try:
            hour = int(self.hour_var.get())
            minute = int(self.minute_var.get())
            self.result = datetime.combine(
                self.selected_date,
                datetime.min.time().replace(hour=hour, minute=minute)
            )
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid time format")


class ProgressBar(ttk.Frame):
    """Custom progress bar with label"""

    def __init__(self, parent, **kwargs):
        super().__init__(parent)
        self.progress_var = tk.IntVar(value=0)

        self.progress = ttk.Progressbar(self, variable=self.progress_var,
                                        maximum=100, length=150)
        self.progress.pack(side='left', padx=5)

        self.label = ttk.Label(self, text="0%", width=5)
        self.label.pack(side='left')

    def set(self, value: int):
        """Set progress value"""
        self.progress_var.set(value)
        self.label.config(text=f"{value}%")

    def get(self) -> int:
        """Get progress value"""
        return self.progress_var.get()


# ============================================================================
# Main Application
# ============================================================================

class PersonalTracker(tk.Tk):
    """Main application class"""

    # Constants
    CLASSIFICATIONS = [
        "Gym Goals",
        "Daily Goals",
        "Work Goals",
        "Certification Goals",
        "Tool Building",
        "Personal",
        "Health",
        "Learning",
        "Other"
    ]

    IMPORTANCE_LEVELS = ["Critical", "High", "Medium", "Low"]

    IMPORTANCE_COLORS = {
        "Critical": "#FF4444",
        "High": "#FFA500",
        "Medium": "#4A90D9",
        "Low": "#90EE90"
    }

    DUE_TYPES = ["None", "Ongoing", "Specific Date"]

    def __init__(self):
        super().__init__()

        self.title("Personal Task Tracker")
        self.geometry("1200x800")
        self.minsize(1000, 600)

        # Initialize data manager
        self.data_manager = DataManager()

        # Configure styles
        self._configure_styles()

        # Create main UI
        self._create_menu()
        self._create_main_layout()

        # Load initial data
        self._refresh_task_list()
        self._refresh_backtrack_list()
        self._update_statistics()

        # Bind window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')

        # Custom styles
        style.configure('Critical.TFrame', background='#FF4444')
        style.configure('High.TFrame', background='#FFA500')
        style.configure('Medium.TFrame', background='#4A90D9')
        style.configure('Low.TFrame', background='#90EE90')

        style.configure('Header.TLabel', font=('Arial', 14, 'bold'))
        style.configure('Subheader.TLabel', font=('Arial', 11, 'bold'))
        style.configure('Stats.TLabel', font=('Arial', 10))

        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))

    def _create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self)
        self.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Export to CSV", command=self._export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self._refresh_all)
        view_menu.add_command(label="Statistics", command=self._show_statistics_dialog)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self._show_about)
        help_menu.add_command(label="Keyboard Shortcuts", command=self._show_shortcuts)

    def _create_main_layout(self):
        """Create the main application layout"""
        # Main container with padding
        main_container = ttk.Frame(self, padding="10")
        main_container.pack(fill='both', expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_container)
        self.notebook.pack(fill='both', expand=True)

        # Tasks tab
        self.tasks_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.tasks_frame, text="Tasks")
        self._create_tasks_tab()

        # Backtrack/Ideas tab
        self.backtrack_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.backtrack_frame, text="Backtrack (Ideas)")
        self._create_backtrack_tab()

        # Statistics tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.stats_frame, text="Statistics")
        self._create_statistics_tab()

        # History tab
        self.history_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.history_frame, text="Completed History")
        self._create_history_tab()

    def _create_tasks_tab(self):
        """Create the tasks management tab"""
        # Top toolbar
        toolbar = ttk.Frame(self.tasks_frame)
        toolbar.pack(fill='x', pady=(0, 10))

        # Add task button
        ttk.Button(toolbar, text="+ Add Task", style='Accent.TButton',
                  command=self._show_add_task_dialog).pack(side='left', padx=5)

        # Search
        ttk.Label(toolbar, text="Search:").pack(side='left', padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._refresh_task_list())
        ttk.Entry(toolbar, textvariable=self.search_var, width=25).pack(side='left')

        # Filter by classification
        ttk.Label(toolbar, text="Category:").pack(side='left', padx=(20, 5))
        self.filter_class_var = tk.StringVar(value="All")
        filter_class = ttk.Combobox(toolbar, textvariable=self.filter_class_var,
                                   values=["All"] + self.CLASSIFICATIONS, width=15, state='readonly')
        filter_class.pack(side='left')
        filter_class.bind('<<ComboboxSelected>>', lambda e: self._refresh_task_list())

        # Filter by importance
        ttk.Label(toolbar, text="Importance:").pack(side='left', padx=(20, 5))
        self.filter_imp_var = tk.StringVar(value="All")
        filter_imp = ttk.Combobox(toolbar, textvariable=self.filter_imp_var,
                                 values=["All"] + self.IMPORTANCE_LEVELS, width=10, state='readonly')
        filter_imp.pack(side='left')
        filter_imp.bind('<<ComboboxSelected>>', lambda e: self._refresh_task_list())

        # Quick stats
        self.quick_stats_label = ttk.Label(toolbar, text="", style='Stats.TLabel')
        self.quick_stats_label.pack(side='right', padx=10)

        # Tasks list with scrollbar
        list_container = ttk.Frame(self.tasks_frame)
        list_container.pack(fill='both', expand=True)

        # Create treeview for tasks
        columns = ('name', 'classification', 'importance', 'due', 'progress')
        self.task_tree = ttk.Treeview(list_container, columns=columns, show='headings',
                                      selectmode='browse')

        # Configure columns
        self.task_tree.heading('name', text='Task Name', anchor='w')
        self.task_tree.heading('classification', text='Category', anchor='w')
        self.task_tree.heading('importance', text='Importance', anchor='w')
        self.task_tree.heading('due', text='Due Date', anchor='w')
        self.task_tree.heading('progress', text='Progress', anchor='w')

        self.task_tree.column('name', width=300, minwidth=200)
        self.task_tree.column('classification', width=150, minwidth=100)
        self.task_tree.column('importance', width=100, minwidth=80)
        self.task_tree.column('due', width=150, minwidth=100)
        self.task_tree.column('progress', width=100, minwidth=80)

        # Scrollbars
        v_scroll = ttk.Scrollbar(list_container, orient='vertical',
                                command=self.task_tree.yview)
        h_scroll = ttk.Scrollbar(list_container, orient='horizontal',
                                command=self.task_tree.xview)
        self.task_tree.configure(yscrollcommand=v_scroll.set,
                                xscrollcommand=h_scroll.set)

        # Grid layout
        self.task_tree.grid(row=0, column=0, sticky='nsew')
        v_scroll.grid(row=0, column=1, sticky='ns')
        h_scroll.grid(row=1, column=0, sticky='ew')

        list_container.columnconfigure(0, weight=1)
        list_container.rowconfigure(0, weight=1)

        # Configure tags for importance colors
        for imp, color in self.IMPORTANCE_COLORS.items():
            self.task_tree.tag_configure(imp, background=color)

        # Bind double-click to edit
        self.task_tree.bind('<Double-1>', self._on_task_double_click)

        # Context menu
        self.task_context_menu = tk.Menu(self, tearoff=0)
        self.task_context_menu.add_command(label="Edit", command=self._edit_selected_task)
        self.task_context_menu.add_command(label="Mark Complete",
                                          command=self._complete_selected_task)
        self.task_context_menu.add_command(label="Update Progress",
                                          command=self._update_task_progress)
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label="Delete", command=self._delete_selected_task)

        self.task_tree.bind('<Button-3>', self._show_task_context_menu)

        # Bottom action buttons
        action_frame = ttk.Frame(self.tasks_frame)
        action_frame.pack(fill='x', pady=(10, 0))

        ttk.Button(action_frame, text="Complete Task",
                  command=self._complete_selected_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Edit Task",
                  command=self._edit_selected_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Delete Task",
                  command=self._delete_selected_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Update Progress",
                  command=self._update_task_progress).pack(side='left', padx=5)

    def _create_backtrack_tab(self):
        """Create the backtrack/ideas tab"""
        # Header
        header_frame = ttk.Frame(self.backtrack_frame)
        header_frame.pack(fill='x', pady=(0, 10))

        ttk.Label(header_frame, text="Backtrack - Ideas & Future Tasks",
                 style='Header.TLabel').pack(side='left')
        ttk.Label(header_frame,
                 text="Store ideas for tasks you haven't scheduled yet",
                 style='Stats.TLabel').pack(side='left', padx=20)

        # Add idea section
        add_frame = ttk.LabelFrame(self.backtrack_frame, text="Add New Idea", padding="10")
        add_frame.pack(fill='x', pady=(0, 10))

        # Idea entry
        entry_frame = ttk.Frame(add_frame)
        entry_frame.pack(fill='x')

        ttk.Label(entry_frame, text="Idea:").pack(side='left')
        self.idea_entry = ttk.Entry(entry_frame, width=50)
        self.idea_entry.pack(side='left', padx=10, fill='x', expand=True)

        ttk.Label(entry_frame, text="Category:").pack(side='left', padx=(10, 5))
        self.idea_class_var = tk.StringVar(value="Other")
        ttk.Combobox(entry_frame, textvariable=self.idea_class_var,
                    values=self.CLASSIFICATIONS, width=15, state='readonly').pack(side='left')

        ttk.Button(entry_frame, text="Add Idea",
                  command=self._add_backtrack_idea).pack(side='left', padx=10)

        # Notes
        notes_frame = ttk.Frame(add_frame)
        notes_frame.pack(fill='x', pady=(10, 0))

        ttk.Label(notes_frame, text="Notes (optional):").pack(side='left')
        self.idea_notes_entry = ttk.Entry(notes_frame, width=80)
        self.idea_notes_entry.pack(side='left', padx=10, fill='x', expand=True)

        # Ideas list
        list_frame = ttk.LabelFrame(self.backtrack_frame, text="Stored Ideas", padding="10")
        list_frame.pack(fill='both', expand=True)

        # Create treeview
        columns = ('idea', 'category', 'notes', 'created')
        self.backtrack_tree = ttk.Treeview(list_frame, columns=columns,
                                          show='headings', selectmode='browse')

        self.backtrack_tree.heading('idea', text='Idea', anchor='w')
        self.backtrack_tree.heading('category', text='Category', anchor='w')
        self.backtrack_tree.heading('notes', text='Notes', anchor='w')
        self.backtrack_tree.heading('created', text='Added On', anchor='w')

        self.backtrack_tree.column('idea', width=300)
        self.backtrack_tree.column('category', width=120)
        self.backtrack_tree.column('notes', width=300)
        self.backtrack_tree.column('created', width=150)

        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient='vertical',
                                 command=self.backtrack_tree.yview)
        self.backtrack_tree.configure(yscrollcommand=scrollbar.set)

        self.backtrack_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Action buttons
        action_frame = ttk.Frame(self.backtrack_frame)
        action_frame.pack(fill='x', pady=(10, 0))

        ttk.Button(action_frame, text="Promote to Task",
                  command=self._promote_idea_to_task).pack(side='left', padx=5)
        ttk.Button(action_frame, text="Delete Idea",
                  command=self._delete_backtrack_idea).pack(side='left', padx=5)

    def _create_statistics_tab(self):
        """Create the statistics dashboard tab"""
        # Main stats container
        stats_container = ttk.Frame(self.stats_frame, padding="20")
        stats_container.pack(fill='both', expand=True)

        # Overview section
        overview_frame = ttk.LabelFrame(stats_container, text="Overview", padding="15")
        overview_frame.pack(fill='x', pady=(0, 20))

        self.stats_labels = {}

        # Grid of stats
        stats_grid = ttk.Frame(overview_frame)
        stats_grid.pack(fill='x')

        stat_items = [
            ('active_tasks', 'Active Tasks'),
            ('due_today', 'Due Today'),
            ('overdue', 'Overdue'),
            ('total_completed', 'Total Completed'),
            ('total_created', 'Total Created'),
            ('backtrack_ideas', 'Backtrack Ideas')
        ]

        for i, (key, label) in enumerate(stat_items):
            frame = ttk.Frame(stats_grid)
            frame.grid(row=i//3, column=i%3, padx=20, pady=10, sticky='w')

            ttk.Label(frame, text=label + ":", style='Subheader.TLabel').pack(anchor='w')
            self.stats_labels[key] = ttk.Label(frame, text="0",
                                               font=('Arial', 24, 'bold'))
            self.stats_labels[key].pack(anchor='w')

        # By Category
        by_class_frame = ttk.LabelFrame(stats_container, text="Tasks by Category", padding="15")
        by_class_frame.pack(fill='both', expand=True, side='left', padx=(0, 10))

        self.class_stats_text = tk.Text(by_class_frame, height=10, width=40,
                                        state='disabled', font=('Arial', 10))
        self.class_stats_text.pack(fill='both', expand=True)

        # By Importance
        by_imp_frame = ttk.LabelFrame(stats_container, text="Tasks by Importance", padding="15")
        by_imp_frame.pack(fill='both', expand=True, side='left', padx=(0, 10))

        self.imp_stats_text = tk.Text(by_imp_frame, height=10, width=40,
                                      state='disabled', font=('Arial', 10))
        self.imp_stats_text.pack(fill='both', expand=True)

        # Streaks
        streaks_frame = ttk.LabelFrame(stats_container, text="Current Streaks", padding="15")
        streaks_frame.pack(fill='both', expand=True, side='left')

        self.streaks_text = tk.Text(streaks_frame, height=10, width=40,
                                    state='disabled', font=('Arial', 10))
        self.streaks_text.pack(fill='both', expand=True)

    def _create_history_tab(self):
        """Create the completed history tab"""
        # Header
        ttk.Label(self.history_frame, text="Completed Tasks History",
                 style='Header.TLabel').pack(pady=(0, 10))

        # Create treeview
        columns = ('name', 'classification', 'importance', 'completed_at')
        self.history_tree = ttk.Treeview(self.history_frame, columns=columns,
                                        show='headings', selectmode='browse')

        self.history_tree.heading('name', text='Task Name', anchor='w')
        self.history_tree.heading('classification', text='Category', anchor='w')
        self.history_tree.heading('importance', text='Importance', anchor='w')
        self.history_tree.heading('completed_at', text='Completed At', anchor='w')

        self.history_tree.column('name', width=350)
        self.history_tree.column('classification', width=150)
        self.history_tree.column('importance', width=100)
        self.history_tree.column('completed_at', width=200)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.history_frame, orient='vertical',
                                 command=self.history_tree.yview)
        self.history_tree.configure(yscrollcommand=scrollbar.set)

        self.history_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self._refresh_history_list()

    # ========================================================================
    # Task Operations
    # ========================================================================

    def _show_add_task_dialog(self, edit_task=None):
        """Show dialog to add or edit a task"""
        dialog = tk.Toplevel(self)
        dialog.title("Edit Task" if edit_task else "Add New Task")
        dialog.geometry("500x550")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill='both', expand=True)

        # Task name
        ttk.Label(main_frame, text="Task Name:", style='Subheader.TLabel').pack(anchor='w')
        name_entry = ttk.Entry(main_frame, width=50)
        name_entry.pack(fill='x', pady=(0, 15))
        if edit_task:
            name_entry.insert(0, edit_task.get('name', ''))

        # Classification
        ttk.Label(main_frame, text="Category:", style='Subheader.TLabel').pack(anchor='w')
        class_var = tk.StringVar(value=edit_task.get('classification', 'Other') if edit_task else 'Other')
        class_combo = ttk.Combobox(main_frame, textvariable=class_var,
                                  values=self.CLASSIFICATIONS, state='readonly')
        class_combo.pack(fill='x', pady=(0, 15))

        # Importance
        ttk.Label(main_frame, text="Importance:", style='Subheader.TLabel').pack(anchor='w')
        imp_var = tk.StringVar(value=edit_task.get('importance', 'Medium') if edit_task else 'Medium')
        imp_frame = ttk.Frame(main_frame)
        imp_frame.pack(fill='x', pady=(0, 15))

        for imp in self.IMPORTANCE_LEVELS:
            ttk.Radiobutton(imp_frame, text=imp, variable=imp_var,
                           value=imp).pack(side='left', padx=10)

        # Due date type
        ttk.Label(main_frame, text="Due Date:", style='Subheader.TLabel').pack(anchor='w')
        due_type_var = tk.StringVar(value=edit_task.get('due_type', 'None') if edit_task else 'None')
        due_frame = ttk.Frame(main_frame)
        due_frame.pack(fill='x', pady=(0, 5))

        for due_type in self.DUE_TYPES:
            ttk.Radiobutton(due_frame, text=due_type, variable=due_type_var,
                           value=due_type.lower().replace(' ', '_')).pack(side='left', padx=10)

        # Date selection
        date_frame = ttk.Frame(main_frame)
        date_frame.pack(fill='x', pady=(0, 15))

        date_label = ttk.Label(date_frame, text="No date selected")
        date_label.pack(side='left')

        selected_date = [None]
        if edit_task and edit_task.get('due_date'):
            try:
                selected_date[0] = datetime.fromisoformat(edit_task['due_date'])
                date_label.config(text=selected_date[0].strftime("%Y-%m-%d %H:%M"))
            except (ValueError, TypeError):
                pass

        def pick_date():
            picker = DateTimePicker(dialog, selected_date[0])
            dialog.wait_window(picker)
            if picker.result:
                selected_date[0] = picker.result
                date_label.config(text=picker.result.strftime("%Y-%m-%d %H:%M"))

        ttk.Button(date_frame, text="Pick Date/Time",
                  command=pick_date).pack(side='left', padx=10)

        # Progress
        ttk.Label(main_frame, text="Progress:", style='Subheader.TLabel').pack(anchor='w')
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill='x', pady=(0, 15))

        progress_var = tk.IntVar(value=edit_task.get('progress', 0) if edit_task else 0)
        progress_scale = ttk.Scale(progress_frame, from_=0, to=100,
                                  variable=progress_var, orient='horizontal', length=300)
        progress_scale.pack(side='left')

        progress_label = ttk.Label(progress_frame, text=f"{progress_var.get()}%")
        progress_label.pack(side='left', padx=10)

        def update_progress_label(*args):
            progress_label.config(text=f"{int(progress_var.get())}%")
        progress_var.trace('w', update_progress_label)

        # Notes
        ttk.Label(main_frame, text="Notes:", style='Subheader.TLabel').pack(anchor='w')
        notes_text = tk.Text(main_frame, height=4, width=50)
        notes_text.pack(fill='x', pady=(0, 15))
        if edit_task:
            notes_text.insert('1.0', edit_task.get('notes', ''))

        # Recurring option
        recurring_var = tk.BooleanVar(value=edit_task.get('recurring', False) if edit_task else False)
        ttk.Checkbutton(main_frame, text="Recurring task (recreate when completed)",
                       variable=recurring_var).pack(anchor='w', pady=(0, 15))

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x')

        def save_task():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror("Error", "Task name is required")
                return

            task_data = {
                'name': name,
                'classification': class_var.get(),
                'importance': imp_var.get(),
                'due_type': due_type_var.get(),
                'due_date': selected_date[0].isoformat() if selected_date[0] else None,
                'progress': int(progress_var.get()),
                'notes': notes_text.get('1.0', 'end-1c').strip(),
                'recurring': recurring_var.get(),
                'status': 'active'
            }

            if edit_task:
                self.data_manager.update_task(edit_task['id'], task_data)
            else:
                self.data_manager.add_task(task_data)

            dialog.destroy()
            self._refresh_task_list()
            self._update_statistics()

        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Save", command=save_task,
                  style='Accent.TButton').pack(side='right')

    def _refresh_task_list(self):
        """Refresh the task list display"""
        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)

        # Build filters
        filters = {}
        if self.search_var.get():
            filters['search'] = self.search_var.get()
        if self.filter_class_var.get() != "All":
            filters['classification'] = self.filter_class_var.get()
        if self.filter_imp_var.get() != "All":
            filters['importance'] = self.filter_imp_var.get()

        # Get and display tasks
        tasks = self.data_manager.get_tasks(filters if filters else None)

        # Sort by importance then due date
        importance_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
        tasks.sort(key=lambda t: (importance_order.get(t.get('importance', 'Medium'), 2),
                                  t.get('due_date') or '9999'))

        for task in tasks:
            due_display = self._format_due_date(task)
            values = (
                task.get('name', ''),
                task.get('classification', ''),
                task.get('importance', ''),
                due_display,
                f"{task.get('progress', 0)}%"
            )
            self.task_tree.insert('', 'end', iid=task['id'], values=values,
                                 tags=(task.get('importance', 'Medium'),))

        # Update quick stats
        stats = self.data_manager.get_statistics()
        self.quick_stats_label.config(
            text=f"Active: {stats['active_tasks']} | Due Today: {stats['due_today']} | Overdue: {stats['overdue']}"
        )

    def _format_due_date(self, task: Dict) -> str:
        """Format due date for display"""
        due_type = task.get('due_type', 'none')
        if due_type == 'none':
            return "No due date"
        elif due_type == 'ongoing':
            return "Ongoing"
        elif due_type == 'specific_date' and task.get('due_date'):
            try:
                due = datetime.fromisoformat(task['due_date'])
                today = datetime.now().date()
                due_date = due.date()

                if due_date == today:
                    return f"Today {due.strftime('%H:%M')}"
                elif due_date == today + timedelta(days=1):
                    return f"Tomorrow {due.strftime('%H:%M')}"
                elif due_date < today:
                    return f"OVERDUE: {due.strftime('%Y-%m-%d')}"
                else:
                    return due.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                return "Invalid date"
        return "No due date"

    def _on_task_double_click(self, event):
        """Handle double-click on task"""
        self._edit_selected_task()

    def _show_task_context_menu(self, event):
        """Show context menu for tasks"""
        item = self.task_tree.identify_row(event.y)
        if item:
            self.task_tree.selection_set(item)
            self.task_context_menu.tk_popup(event.x_root, event.y_root)

    def _get_selected_task(self) -> Optional[Dict]:
        """Get currently selected task"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select a task first")
            return None

        task_id = selection[0]
        for task in self.data_manager.get_tasks():
            if task['id'] == task_id:
                return task
        return None

    def _edit_selected_task(self):
        """Edit the selected task"""
        task = self._get_selected_task()
        if task:
            self._show_add_task_dialog(edit_task=task)

    def _delete_selected_task(self):
        """Delete the selected task"""
        task = self._get_selected_task()
        if task:
            if messagebox.askyesno("Confirm Delete",
                                  f"Delete task '{task['name']}'?"):
                self.data_manager.delete_task(task['id'])
                self._refresh_task_list()
                self._update_statistics()

    def _complete_selected_task(self):
        """Mark selected task as complete"""
        task = self._get_selected_task()
        if task:
            self.data_manager.complete_task(task['id'])

            # If recurring, create new task
            if task.get('recurring'):
                new_task = task.copy()
                new_task.pop('id', None)
                new_task.pop('created_at', None)
                new_task['progress'] = 0
                self.data_manager.add_task(new_task)

            self._refresh_task_list()
            self._refresh_history_list()
            self._update_statistics()
            messagebox.showinfo("Success", f"Task '{task['name']}' completed!")

    def _update_task_progress(self):
        """Update progress of selected task"""
        task = self._get_selected_task()
        if not task:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Update Progress")
        dialog.geometry("300x150")
        dialog.transient(self)
        dialog.grab_set()

        # Center
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill='both', expand=True)

        ttk.Label(frame, text=f"Progress for: {task['name'][:40]}...").pack()

        progress_var = tk.IntVar(value=task.get('progress', 0))
        scale = ttk.Scale(frame, from_=0, to=100, variable=progress_var,
                         orient='horizontal', length=200)
        scale.pack(pady=10)

        label = ttk.Label(frame, text=f"{progress_var.get()}%")
        label.pack()

        def update_label(*args):
            label.config(text=f"{int(progress_var.get())}%")
        progress_var.trace('w', update_label)

        def save():
            self.data_manager.update_task(task['id'], {'progress': int(progress_var.get())})
            dialog.destroy()
            self._refresh_task_list()

        ttk.Button(frame, text="Save", command=save).pack(pady=10)

    # ========================================================================
    # Backtrack Operations
    # ========================================================================

    def _add_backtrack_idea(self):
        """Add a new idea to backtrack"""
        idea_text = self.idea_entry.get().strip()
        if not idea_text:
            messagebox.showerror("Error", "Please enter an idea")
            return

        idea = {
            'text': idea_text,
            'classification': self.idea_class_var.get(),
            'notes': self.idea_notes_entry.get().strip()
        }

        self.data_manager.add_backtrack(idea)
        self.idea_entry.delete(0, 'end')
        self.idea_notes_entry.delete(0, 'end')
        self._refresh_backtrack_list()
        self._update_statistics()

    def _refresh_backtrack_list(self):
        """Refresh the backtrack list"""
        for item in self.backtrack_tree.get_children():
            self.backtrack_tree.delete(item)

        for idea in self.data_manager.get_backtrack():
            created = ""
            if idea.get('created_at'):
                try:
                    created = datetime.fromisoformat(idea['created_at']).strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    pass

            values = (
                idea.get('text', ''),
                idea.get('classification', ''),
                idea.get('notes', ''),
                created
            )
            self.backtrack_tree.insert('', 'end', iid=idea['id'], values=values)

    def _promote_idea_to_task(self):
        """Promote a backtrack idea to a task"""
        selection = self.backtrack_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select an idea to promote")
            return

        idea_id = selection[0]
        idea = self.data_manager.promote_backtrack(idea_id)

        if idea:
            # Open task dialog with pre-filled data
            task_data = {
                'name': idea.get('text', ''),
                'classification': idea.get('classification', 'Other'),
                'notes': idea.get('notes', ''),
                'importance': 'Medium',
                'due_type': 'none',
                'progress': 0
            }
            self._show_add_task_dialog(edit_task={'id': 'new', **task_data})
            self._refresh_backtrack_list()

    def _delete_backtrack_idea(self):
        """Delete a backtrack idea"""
        selection = self.backtrack_tree.selection()
        if not selection:
            messagebox.showinfo("Info", "Please select an idea to delete")
            return

        if messagebox.askyesno("Confirm Delete", "Delete this idea?"):
            self.data_manager.delete_backtrack(selection[0])
            self._refresh_backtrack_list()
            self._update_statistics()

    # ========================================================================
    # Statistics Operations
    # ========================================================================

    def _update_statistics(self):
        """Update statistics display"""
        stats = self.data_manager.get_statistics()

        # Update main stats
        for key in ['active_tasks', 'due_today', 'overdue', 'total_completed',
                   'total_created', 'backtrack_ideas']:
            if key in self.stats_labels:
                self.stats_labels[key].config(text=str(stats.get(key, 0)))

        # Update by classification
        self.class_stats_text.config(state='normal')
        self.class_stats_text.delete('1.0', 'end')
        for cls, count in stats.get('by_classification', {}).items():
            self.class_stats_text.insert('end', f"{cls}: {count}\n")
        self.class_stats_text.config(state='disabled')

        # Update by importance
        self.imp_stats_text.config(state='normal')
        self.imp_stats_text.delete('1.0', 'end')
        for imp in self.IMPORTANCE_LEVELS:
            count = stats.get('by_importance', {}).get(imp, 0)
            self.imp_stats_text.insert('end', f"{imp}: {count}\n")
        self.imp_stats_text.config(state='disabled')

        # Update streaks
        self.streaks_text.config(state='normal')
        self.streaks_text.delete('1.0', 'end')
        for cls, streak_data in stats.get('streaks', {}).items():
            self.streaks_text.insert('end',
                f"{cls}:\n  Current: {streak_data['current']} days\n  Best: {streak_data['best']} days\n\n")
        self.streaks_text.config(state='disabled')

    def _refresh_history_list(self):
        """Refresh the completed history list"""
        for item in self.history_tree.get_children():
            self.history_tree.delete(item)

        for task in reversed(self.data_manager.data.get('completed_history', [])):
            completed = ""
            if task.get('completed_at'):
                try:
                    completed = datetime.fromisoformat(task['completed_at']).strftime("%Y-%m-%d %H:%M")
                except (ValueError, TypeError):
                    pass

            values = (
                task.get('name', ''),
                task.get('classification', ''),
                task.get('importance', ''),
                completed
            )
            self.history_tree.insert('', 'end', values=values)

    def _refresh_all(self):
        """Refresh all displays"""
        self._refresh_task_list()
        self._refresh_backtrack_list()
        self._refresh_history_list()
        self._update_statistics()

    # ========================================================================
    # Menu Operations
    # ========================================================================

    def _export_csv(self):
        """Export tasks to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Tasks to CSV"
        )
        if filename:
            self.data_manager.export_to_csv(filename)
            messagebox.showinfo("Success", f"Tasks exported to {filename}")

    def _show_statistics_dialog(self):
        """Show statistics in a dialog"""
        self.notebook.select(self.stats_frame)

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About Personal Task Tracker",
            "Personal Task Tracker v1.0\n\n"
            "A comprehensive task management application\n\n"
            "Features:\n"
            "- Task management with priorities\n"
            "- Category-based organization\n"
            "- Progress tracking\n"
            "- Backtrack ideas storage\n"
            "- Statistics dashboard\n"
            "- Data persistence\n"
            "- Export to CSV"
        )

    def _show_shortcuts(self):
        """Show keyboard shortcuts"""
        messagebox.showinfo("Keyboard Shortcuts",
            "Keyboard Shortcuts:\n\n"
            "Double-click: Edit task\n"
            "Right-click: Context menu\n"
            "Ctrl+N: New task (in Tasks tab)\n"
            "Delete: Delete selected item"
        )

    def _on_close(self):
        """Handle window close"""
        self.data_manager.save_data()
        self.destroy()


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point"""
    app = PersonalTracker()

    # Bind keyboard shortcuts
    app.bind('<Control-n>', lambda e: app._show_add_task_dialog())
    app.bind('<Delete>', lambda e: app._delete_selected_task()
             if app.notebook.index(app.notebook.select()) == 0 else None)

    app.mainloop()


if __name__ == "__main__":
    main()

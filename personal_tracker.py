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
- Export/Import functionality
- Pomodoro Timer for focused work
- Dark/Light theme toggle
- Task duplication and snoozing
- Daily review and backup
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import json
import os
import uuid
from typing import Optional, Dict, List, Any, Callable
import csv
import shutil
import threading
try:
    # Optional: for sound notifications
    import winsound
    HAS_SOUND = True
except ImportError:
    HAS_SOUND = False


# ============================================================================
# Data Models and Storage
# ============================================================================

class DataManager:
    """Handles data persistence using JSON files"""

    def __init__(self, data_file: str = None):
        # Store data file in same directory as script, not CWD
        if data_file is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            self.data_file = os.path.join(script_dir, "tracker_data.json")
        else:
            self.data_file = data_file
        self.data = self._load_data()

    def _load_data(self) -> Dict[str, Any]:
        """Load data from JSON file"""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    data = json.load(f)
                    # Ensure all required keys exist (data migration)
                    default = self._get_default_data()
                    for key in default:
                        if key not in data:
                            data[key] = default[key]
                    return data
            except json.JSONDecodeError as e:
                # Backup corrupted file and warn user
                backup_file = self.data_file + ".corrupted"
                try:
                    os.rename(self.data_file, backup_file)
                except OSError:
                    pass
                messagebox.showwarning(
                    "Data Warning",
                    f"Data file was corrupted and has been reset.\n"
                    f"Backup saved to: {backup_file}"
                )
                return self._get_default_data()
            except IOError as e:
                messagebox.showwarning("Data Warning", f"Could not read data file: {e}")
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
        # Skip empty classifications
        if not classification or not classification.strip():
            return

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

            if diff == 0:
                # Same day - streak continues but don't increment
                pass
            elif diff == 1:
                # Next day - increment streak
                streak['current'] += 1
            else:
                # Missed days - reset streak
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
            if task.get('due_date') and task.get('due_type') == 'specific_date':
                try:
                    due = datetime.fromisoformat(task['due_date']).date()
                    if due == today:
                        stats['due_today'] += 1
                    elif due < today:
                        stats['overdue'] += 1
                except (ValueError, TypeError):
                    pass

        return stats

    def export_to_csv(self, filename: str) -> bool:
        """Export tasks to CSV. Returns True on success, False on failure."""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as f:
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
            return True
        except (IOError, OSError) as e:
            messagebox.showerror("Export Error", f"Failed to export CSV: {e}")
            return False

    def import_from_csv(self, filename: str) -> tuple[int, int]:
        """Import tasks from CSV. Returns (success_count, error_count)."""
        success = 0
        errors = 0
        try:
            with open(filename, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    try:
                        task = {
                            'name': row.get('Name', row.get('name', '')),
                            'classification': row.get('Classification', row.get('classification', 'Other')),
                            'importance': row.get('Importance', row.get('importance', 'Medium')),
                            'due_type': row.get('Due Type', row.get('due_type', 'none')),
                            'due_date': row.get('Due Date', row.get('due_date', None)) or None,
                            'progress': int(row.get('Progress', row.get('progress', 0)) or 0),
                            'notes': row.get('Notes', row.get('notes', '')),
                            'recurring': False,
                            'status': 'active'
                        }
                        if task['name']:
                            self.add_task(task)
                            success += 1
                    except (ValueError, KeyError):
                        errors += 1
        except (IOError, OSError) as e:
            messagebox.showerror("Import Error", f"Failed to import CSV: {e}")
        return success, errors

    def create_backup(self, backup_dir: str = None) -> Optional[str]:
        """Create a backup of the data file. Returns backup path or None."""
        if backup_dir is None:
            backup_dir = os.path.dirname(self.data_file)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"tracker_backup_{timestamp}.json"
        backup_path = os.path.join(backup_dir, backup_name)

        try:
            shutil.copy2(self.data_file, backup_path)
            return backup_path
        except (IOError, OSError) as e:
            messagebox.showerror("Backup Error", f"Failed to create backup: {e}")
            return None

    def restore_backup(self, backup_path: str) -> bool:
        """Restore data from a backup file."""
        try:
            with open(backup_path, 'r') as f:
                data = json.load(f)
                # Validate structure
                if 'tasks' in data and 'backtrack' in data:
                    self.data = data
                    self.save_data()
                    return True
                else:
                    messagebox.showerror("Restore Error", "Invalid backup file format")
                    return False
        except (json.JSONDecodeError, IOError) as e:
            messagebox.showerror("Restore Error", f"Failed to restore: {e}")
            return False

    def get_daily_summary(self) -> Dict:
        """Get summary of today's tasks and completed tasks."""
        today = datetime.now().date()
        today_str = today.strftime("%Y-%m-%d")

        summary = {
            'due_today': [],
            'overdue': [],
            'completed_today': [],
            'in_progress': []
        }

        # Check active tasks
        for task in self.data['tasks']:
            if task.get('due_type') == 'specific_date' and task.get('due_date'):
                try:
                    due = datetime.fromisoformat(task['due_date']).date()
                    if due == today:
                        summary['due_today'].append(task)
                    elif due < today:
                        summary['overdue'].append(task)
                except (ValueError, TypeError):
                    pass

            if task.get('progress', 0) > 0 and task.get('progress', 0) < 100:
                summary['in_progress'].append(task)

        # Check completed today
        for task in self.data.get('completed_history', []):
            if task.get('completed_at'):
                try:
                    completed = datetime.fromisoformat(task['completed_at']).date()
                    if completed == today:
                        summary['completed_today'].append(task)
                except (ValueError, TypeError):
                    pass

        return summary

    def snooze_task(self, task_id: str, days: int) -> bool:
        """Snooze a task by the specified number of days."""
        for task in self.data['tasks']:
            if task['id'] == task_id:
                if task.get('due_date'):
                    try:
                        current_due = datetime.fromisoformat(task['due_date'])
                        new_due = current_due + timedelta(days=days)
                        task['due_date'] = new_due.isoformat()
                    except (ValueError, TypeError):
                        new_due = datetime.now() + timedelta(days=days)
                        task['due_date'] = new_due.isoformat()
                else:
                    new_due = datetime.now() + timedelta(days=days)
                    task['due_date'] = new_due.isoformat()
                    task['due_type'] = 'specific_date'

                task['updated_at'] = datetime.now().isoformat()
                self.save_data()
                return True
        return False


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
        year = self.current_date.year
        month = self.current_date.month - 1
        if month < 1:
            month = 12
            year -= 1
        # Handle day overflow (e.g., March 31 -> February 28)
        day = min(self.current_date.day, self._days_in_month(year, month))
        self.current_date = self.current_date.replace(year=year, month=month, day=day)
        self._update_calendar()

    def _next_month(self):
        """Go to next month"""
        year = self.current_date.year
        month = self.current_date.month + 1
        if month > 12:
            month = 1
            year += 1
        # Handle day overflow (e.g., January 31 -> February 28)
        day = min(self.current_date.day, self._days_in_month(year, month))
        self.current_date = self.current_date.replace(year=year, month=month, day=day)
        self._update_calendar()

    def _days_in_month(self, year: int, month: int) -> int:
        """Get number of days in a month"""
        if month == 12:
            next_month = datetime(year + 1, 1, 1)
        else:
            next_month = datetime(year, month + 1, 1)
        return (next_month - datetime(year, month, 1)).days

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

            # Validate ranges
            if not (0 <= hour <= 23):
                messagebox.showerror("Error", "Hour must be between 0 and 23")
                return
            if not (0 <= minute <= 59):
                messagebox.showerror("Error", "Minute must be between 0 and 59")
                return

            self.result = datetime.combine(
                self.selected_date,
                datetime.min.time().replace(hour=hour, minute=minute)
            )
            self.destroy()
        except ValueError:
            messagebox.showerror("Error", "Invalid time format. Use numbers only.")


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


class PomodoroTimer(tk.Toplevel):
    """Pomodoro Timer for focused work sessions"""

    def __init__(self, parent, task_name: str = "Focus Session",
                 work_minutes: int = 25, break_minutes: int = 5,
                 on_complete: Callable = None):
        super().__init__(parent)
        self.title("Pomodoro Timer")
        self.geometry("350x300")
        self.resizable(False, False)
        self.transient(parent)

        self.task_name = task_name
        self.work_seconds = work_minutes * 60
        self.break_seconds = break_minutes * 60
        self.on_complete = on_complete

        self.remaining = self.work_seconds
        self.is_running = False
        self.is_break = False
        self.sessions_completed = 0
        self.timer_id = None

        self._create_widgets()

        # Center the dialog
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _create_widgets(self):
        main_frame = ttk.Frame(self, padding="20")
        main_frame.pack(fill='both', expand=True)

        # Task name
        self.task_label = ttk.Label(main_frame, text=self.task_name,
                                    font=('Arial', 12, 'bold'), wraplength=300)
        self.task_label.pack(pady=(0, 10))

        # Mode indicator
        self.mode_label = ttk.Label(main_frame, text="WORK TIME",
                                    font=('Arial', 10), foreground='#FF4444')
        self.mode_label.pack()

        # Timer display
        self.timer_label = ttk.Label(main_frame, text="25:00",
                                     font=('Arial', 48, 'bold'))
        self.timer_label.pack(pady=20)

        # Progress bar
        self.progress_var = tk.DoubleVar(value=0)
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var,
                                        maximum=100, length=250)
        self.progress.pack(pady=10)

        # Sessions counter
        self.sessions_label = ttk.Label(main_frame, text="Sessions: 0",
                                        font=('Arial', 10))
        self.sessions_label.pack()

        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(pady=15)

        self.start_btn = ttk.Button(btn_frame, text="Start",
                                    command=self._toggle_timer, width=10)
        self.start_btn.pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Reset",
                  command=self._reset_timer, width=10).pack(side='left', padx=5)

        ttk.Button(btn_frame, text="Skip",
                  command=self._skip_phase, width=10).pack(side='left', padx=5)

    def _update_display(self):
        """Update the timer display"""
        mins = self.remaining // 60
        secs = self.remaining % 60
        self.timer_label.config(text=f"{mins:02d}:{secs:02d}")

        # Update progress
        total = self.break_seconds if self.is_break else self.work_seconds
        progress = ((total - self.remaining) / total) * 100
        self.progress_var.set(progress)

    def _toggle_timer(self):
        """Start or pause the timer"""
        if self.is_running:
            self.is_running = False
            self.start_btn.config(text="Resume")
            if self.timer_id:
                self.after_cancel(self.timer_id)
        else:
            self.is_running = True
            self.start_btn.config(text="Pause")
            self._tick()

    def _tick(self):
        """Timer tick"""
        if self.is_running and self.remaining > 0:
            self.remaining -= 1
            self._update_display()
            self.timer_id = self.after(1000, self._tick)
        elif self.remaining <= 0:
            self._phase_complete()

    def _phase_complete(self):
        """Handle phase completion"""
        self.is_running = False
        self.start_btn.config(text="Start")

        # Play notification sound if available
        if HAS_SOUND:
            try:
                winsound.MessageBeep()
            except Exception:
                pass

        if self.is_break:
            # Break finished, back to work
            self.is_break = False
            self.remaining = self.work_seconds
            self.mode_label.config(text="WORK TIME", foreground='#FF4444')
            messagebox.showinfo("Break Over", "Break time is over! Ready for another work session?")
        else:
            # Work finished, time for break
            self.sessions_completed += 1
            self.sessions_label.config(text=f"Sessions: {self.sessions_completed}")
            self.is_break = True
            self.remaining = self.break_seconds
            self.mode_label.config(text="BREAK TIME", foreground='#4A90D9')

            if self.on_complete:
                self.on_complete()

            # Long break every 4 sessions
            if self.sessions_completed % 4 == 0:
                self.remaining = self.break_seconds * 3  # 15 min break
                messagebox.showinfo("Great Work!",
                    f"Completed {self.sessions_completed} sessions!\n"
                    "Take a longer 15-minute break.")
            else:
                messagebox.showinfo("Session Complete",
                    "Work session complete! Time for a short break.")

        self._update_display()

    def _reset_timer(self):
        """Reset the current phase"""
        self.is_running = False
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.start_btn.config(text="Start")
        self.remaining = self.break_seconds if self.is_break else self.work_seconds
        self._update_display()

    def _skip_phase(self):
        """Skip current phase"""
        self.remaining = 0
        self._phase_complete()

    def _on_close(self):
        """Handle window close"""
        if self.timer_id:
            self.after_cancel(self.timer_id)
        self.destroy()


class QuickAddDialog(tk.Toplevel):
    """Quick add dialog for fast task entry"""

    def __init__(self, parent, classifications: List[str], on_save: Callable):
        super().__init__(parent)
        self.title("Quick Add Task")
        self.geometry("400x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.on_save = on_save
        self.classifications = classifications

        self._create_widgets()

        # Center
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 2
        self.geometry(f"+{x}+{y}")

        # Focus on name entry
        self.name_entry.focus_set()

        # Bind Enter to save
        self.bind('<Return>', lambda e: self._save())
        self.bind('<Escape>', lambda e: self.destroy())

    def _create_widgets(self):
        frame = ttk.Frame(self, padding="15")
        frame.pack(fill='both', expand=True)

        # Task name
        ttk.Label(frame, text="Task Name:").grid(row=0, column=0, sticky='w', pady=5)
        self.name_entry = ttk.Entry(frame, width=40)
        self.name_entry.grid(row=0, column=1, columnspan=2, pady=5, sticky='ew')

        # Category
        ttk.Label(frame, text="Category:").grid(row=1, column=0, sticky='w', pady=5)
        self.class_var = tk.StringVar(value="Daily Goals")
        ttk.Combobox(frame, textvariable=self.class_var, values=self.classifications,
                    state='readonly', width=20).grid(row=1, column=1, pady=5, sticky='w')

        # Importance
        ttk.Label(frame, text="Importance:").grid(row=2, column=0, sticky='w', pady=5)
        self.imp_var = tk.StringVar(value="Medium")
        imp_frame = ttk.Frame(frame)
        imp_frame.grid(row=2, column=1, columnspan=2, sticky='w', pady=5)
        for imp in ["Critical", "High", "Medium", "Low"]:
            ttk.Radiobutton(imp_frame, text=imp, variable=self.imp_var,
                           value=imp).pack(side='left', padx=3)

        # Buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)

        ttk.Button(btn_frame, text="Add Task", command=self._save).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side='left', padx=5)

        frame.columnconfigure(1, weight=1)

    def _save(self):
        """Save the task"""
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showerror("Error", "Task name is required")
            return

        task = {
            'name': name,
            'classification': self.class_var.get(),
            'importance': self.imp_var.get(),
            'due_type': 'none',
            'due_date': None,
            'progress': 0,
            'notes': '',
            'recurring': False,
            'status': 'active'
        }

        self.on_save(task)
        self.destroy()


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

    # Theme colors
    THEMES = {
        'light': {
            'bg': '#ffffff',
            'fg': '#000000',
            'select_bg': '#4a90d9',
            'tree_bg': '#ffffff',
            'frame_bg': '#f0f0f0'
        },
        'dark': {
            'bg': '#2d2d2d',
            'fg': '#ffffff',
            'select_bg': '#4a90d9',
            'tree_bg': '#3d3d3d',
            'frame_bg': '#252525'
        }
    }

    def __init__(self):
        super().__init__()

        self.title("Personal Task Tracker")
        self.geometry("1200x800")
        self.minsize(1000, 600)

        # Initialize data manager
        self.data_manager = DataManager()

        # Current theme
        self.current_theme = self.data_manager.data.get('settings', {}).get('theme', 'light')

        # Configure styles
        self._configure_styles()

        # Create main UI
        self._create_menu()
        self._create_main_layout()

        # Load initial data
        self._refresh_task_list()
        self._refresh_backtrack_list()
        self._update_statistics()

        # Apply theme
        self._apply_theme()

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
        file_menu.add_command(label="Quick Add Task (Ctrl+Shift+N)", command=self._show_quick_add)
        file_menu.add_separator()
        file_menu.add_command(label="Export to CSV", command=self._export_csv)
        file_menu.add_command(label="Import from CSV", command=self._import_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Create Backup", command=self._create_backup)
        file_menu.add_command(label="Restore Backup", command=self._restore_backup)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self._on_close)

        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Duplicate Task", command=self._duplicate_selected_task)
        edit_menu.add_command(label="Snooze Task", command=self._snooze_selected_task)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Refresh", command=self._refresh_all)
        view_menu.add_command(label="Statistics", command=self._show_statistics_dialog)
        view_menu.add_command(label="Daily Review", command=self._show_daily_review)
        view_menu.add_separator()
        self.theme_var = tk.StringVar(value=self.current_theme)
        view_menu.add_radiobutton(label="Light Theme", variable=self.theme_var,
                                  value='light', command=self._toggle_theme)
        view_menu.add_radiobutton(label="Dark Theme", variable=self.theme_var,
                                  value='dark', command=self._toggle_theme)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Pomodoro Timer", command=self._start_pomodoro)
        tools_menu.add_command(label="Focus on Task", command=self._focus_on_task)

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
        # Top toolbar row 1
        toolbar = ttk.Frame(self.tasks_frame)
        toolbar.pack(fill='x', pady=(0, 5))

        # Add task button
        ttk.Button(toolbar, text="+ Add Task", style='Accent.TButton',
                  command=self._show_add_task_dialog).pack(side='left', padx=5)

        # Search
        ttk.Label(toolbar, text="Search:").pack(side='left', padx=(20, 5))
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self._refresh_task_list())
        ttk.Entry(toolbar, textvariable=self.search_var, width=20).pack(side='left')

        # View mode toggle
        ttk.Label(toolbar, text="View:").pack(side='left', padx=(15, 5))
        self.view_mode_var = tk.StringVar(value="list")
        view_frame = ttk.Frame(toolbar)
        view_frame.pack(side='left')
        ttk.Radiobutton(view_frame, text="List", variable=self.view_mode_var,
                       value="list", command=self._refresh_task_list).pack(side='left')
        ttk.Radiobutton(view_frame, text="Grouped", variable=self.view_mode_var,
                       value="grouped", command=self._refresh_task_list).pack(side='left')

        # Sort options
        ttk.Label(toolbar, text="Sort:").pack(side='left', padx=(15, 5))
        self.sort_var = tk.StringVar(value="importance")
        sort_combo = ttk.Combobox(toolbar, textvariable=self.sort_var,
                                 values=["importance", "due_date", "progress", "name", "category"],
                                 width=10, state='readonly')
        sort_combo.pack(side='left')
        sort_combo.bind('<<ComboboxSelected>>', lambda e: self._refresh_task_list())

        # Quick stats
        self.quick_stats_label = ttk.Label(toolbar, text="", style='Stats.TLabel')
        self.quick_stats_label.pack(side='right', padx=10)

        # Toolbar row 2 - Quick category filters
        filter_toolbar = ttk.Frame(self.tasks_frame)
        filter_toolbar.pack(fill='x', pady=(0, 5))

        ttk.Label(filter_toolbar, text="Quick Filter:").pack(side='left', padx=5)

        # All button
        self.filter_class_var = tk.StringVar(value="All")
        self.category_buttons = {}

        all_btn = ttk.Button(filter_toolbar, text="All", width=6,
                            command=lambda: self._set_category_filter("All"))
        all_btn.pack(side='left', padx=2)
        self.category_buttons["All"] = all_btn

        # Category buttons with task counts
        for cat in self.CLASSIFICATIONS:
            short_name = cat.split()[0][:6]  # First word, max 6 chars
            btn = ttk.Button(filter_toolbar, text=short_name, width=8,
                            command=lambda c=cat: self._set_category_filter(c))
            btn.pack(side='left', padx=2)
            self.category_buttons[cat] = btn

        # Filter by importance (moved to end)
        ttk.Label(filter_toolbar, text="Importance:").pack(side='left', padx=(15, 5))
        self.filter_imp_var = tk.StringVar(value="All")
        filter_imp = ttk.Combobox(filter_toolbar, textvariable=self.filter_imp_var,
                                 values=["All"] + self.IMPORTANCE_LEVELS, width=10, state='readonly')
        filter_imp.pack(side='left')
        filter_imp.bind('<<ComboboxSelected>>', lambda e: self._refresh_task_list())

        # Main content area with tasks and category overview
        content_frame = ttk.Frame(self.tasks_frame)
        content_frame.pack(fill='both', expand=True)

        # Left side - Task list
        list_container = ttk.Frame(content_frame)
        list_container.pack(side='left', fill='both', expand=True)

        # Create treeview for tasks (with tree column for grouping)
        columns = ('name', 'classification', 'importance', 'due', 'progress')
        self.task_tree = ttk.Treeview(list_container, columns=columns, show='tree headings',
                                      selectmode='browse')

        # Configure tree column (for grouping)
        self.task_tree.heading('#0', text='', anchor='w')
        self.task_tree.column('#0', width=30, minwidth=30, stretch=False)

        # Configure columns
        self.task_tree.heading('name', text='Task Name', anchor='w',
                              command=lambda: self._sort_by_column('name'))
        self.task_tree.heading('classification', text='Category', anchor='w',
                              command=lambda: self._sort_by_column('category'))
        self.task_tree.heading('importance', text='Importance', anchor='w',
                              command=lambda: self._sort_by_column('importance'))
        self.task_tree.heading('due', text='Due Date', anchor='w',
                              command=lambda: self._sort_by_column('due_date'))
        self.task_tree.heading('progress', text='Progress', anchor='w',
                              command=lambda: self._sort_by_column('progress'))

        self.task_tree.column('name', width=280, minwidth=150)
        self.task_tree.column('classification', width=120, minwidth=80)
        self.task_tree.column('importance', width=80, minwidth=60)
        self.task_tree.column('due', width=130, minwidth=100)
        self.task_tree.column('progress', width=80, minwidth=60)

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

        # Tag for group headers
        self.task_tree.tag_configure('group_header', font=('Arial', 10, 'bold'),
                                     background='#e0e0e0')

        # Right side - Category Overview Panel
        overview_frame = ttk.LabelFrame(content_frame, text="Category Overview", padding="10")
        overview_frame.pack(side='right', fill='y', padx=(10, 0))

        self.category_overview = tk.Text(overview_frame, width=25, height=20,
                                        state='disabled', font=('Arial', 9))
        self.category_overview.pack(fill='both', expand=True)

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
        self.task_context_menu.add_command(label="Duplicate", command=self._duplicate_selected_task)
        self.task_context_menu.add_command(label="Snooze", command=self._snooze_selected_task)
        self.task_context_menu.add_command(label="Focus (Pomodoro)", command=self._focus_on_task)
        self.task_context_menu.add_separator()
        self.task_context_menu.add_command(label="Delete", command=self._delete_selected_task)

        self.task_tree.bind('<Button-3>', self._show_task_context_menu)

        # Bottom action buttons
        action_frame = ttk.Frame(self.tasks_frame)
        action_frame.pack(fill='x', pady=(10, 0))

        ttk.Button(action_frame, text="Complete",
                  command=self._complete_selected_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Edit",
                  command=self._edit_selected_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Delete",
                  command=self._delete_selected_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Progress",
                  command=self._update_task_progress).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Duplicate",
                  command=self._duplicate_selected_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Snooze",
                  command=self._snooze_selected_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Focus",
                  command=self._focus_on_task).pack(side='left', padx=3)
        ttk.Button(action_frame, text="Expand All",
                  command=self._expand_all_groups).pack(side='right', padx=3)
        ttk.Button(action_frame, text="Collapse All",
                  command=self._collapse_all_groups).pack(side='right', padx=3)

    def _set_category_filter(self, category: str):
        """Set category filter from quick filter buttons"""
        self.filter_class_var.set(category)
        self._refresh_task_list()

    def _sort_by_column(self, column: str):
        """Sort tasks by clicking column header"""
        self.sort_var.set(column)
        self._refresh_task_list()

    def _expand_all_groups(self):
        """Expand all category groups"""
        for item in self.task_tree.get_children():
            self.task_tree.item(item, open=True)

    def _collapse_all_groups(self):
        """Collapse all category groups"""
        for item in self.task_tree.get_children():
            self.task_tree.item(item, open=False)

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

            # Check if editing existing task (has valid id) or creating new
            if edit_task and edit_task.get('id') and edit_task['id'] != '__prefill__':
                self.data_manager.update_task(edit_task['id'], task_data)
            else:
                self.data_manager.add_task(task_data)
                # If promoting from backtrack, delete the idea now
                if edit_task and edit_task.get('__promote_id__'):
                    self.data_manager.delete_backtrack(edit_task['__promote_id__'])
                    self._refresh_backtrack_list()

            dialog.destroy()
            self._refresh_task_list()
            self._update_statistics()

        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side='right', padx=5)
        ttk.Button(btn_frame, text="Save", command=save_task,
                  style='Accent.TButton').pack(side='right')

    def _show_add_task_dialog_prefilled(self, prefill_data: Dict):
        """Show add task dialog with pre-filled data (for promoting ideas)"""
        # Use special marker id to indicate this is prefilled data, not an edit
        prefill_data['id'] = '__prefill__'
        self._show_add_task_dialog(edit_task=prefill_data)

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

        # Get tasks
        tasks = self.data_manager.get_tasks(filters if filters else None)

        # Sort tasks based on selected sort option
        sort_by = self.sort_var.get()
        importance_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

        if sort_by == "importance":
            tasks.sort(key=lambda t: (importance_order.get(t.get('importance', 'Medium'), 2),
                                      t.get('due_date') or '9999'))
        elif sort_by == "due_date":
            tasks.sort(key=lambda t: (t.get('due_date') or '9999',
                                      importance_order.get(t.get('importance', 'Medium'), 2)))
        elif sort_by == "progress":
            tasks.sort(key=lambda t: (-t.get('progress', 0),
                                      importance_order.get(t.get('importance', 'Medium'), 2)))
        elif sort_by == "name":
            tasks.sort(key=lambda t: t.get('name', '').lower())
        elif sort_by == "category":
            tasks.sort(key=lambda t: (t.get('classification', 'Other'),
                                      importance_order.get(t.get('importance', 'Medium'), 2)))

        # Display based on view mode
        view_mode = self.view_mode_var.get()

        if view_mode == "grouped":
            self._display_grouped_tasks(tasks, importance_order)
        else:
            self._display_list_tasks(tasks)

        # Update quick stats
        stats = self.data_manager.get_statistics()
        self.quick_stats_label.config(
            text=f"Active: {stats['active_tasks']} | Due Today: {stats['due_today']} | Overdue: {stats['overdue']}"
        )

        # Update category overview panel
        self._update_category_overview()

        # Update quick filter button counts
        self._update_filter_button_counts()

    def _display_list_tasks(self, tasks: List[Dict]):
        """Display tasks in flat list view"""
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

    def _display_grouped_tasks(self, tasks: List[Dict], importance_order: Dict):
        """Display tasks grouped by category"""
        # Group tasks by category
        grouped = {}
        for task in tasks:
            cat = task.get('classification', 'Other')
            if cat not in grouped:
                grouped[cat] = []
            grouped[cat].append(task)

        # Sort categories by classification order
        cat_order = {cat: i for i, cat in enumerate(self.CLASSIFICATIONS)}

        # Insert groups
        for cat in sorted(grouped.keys(), key=lambda c: cat_order.get(c, 999)):
            cat_tasks = grouped[cat]

            # Count stats for this category
            total = len(cat_tasks)
            avg_progress = sum(t.get('progress', 0) for t in cat_tasks) // total if total > 0 else 0
            critical_count = sum(1 for t in cat_tasks if t.get('importance') == 'Critical')

            # Create group header
            header_text = f"{cat} ({total} tasks, {avg_progress}% avg)"
            if critical_count > 0:
                header_text = f"{cat} ({total} tasks, {critical_count} critical)"

            group_id = f"_group_{cat.replace(' ', '_')}"
            self.task_tree.insert('', 'end', iid=group_id, text='',
                                 values=(header_text, '', '', '', ''),
                                 tags=('group_header',), open=True)

            # Insert tasks under group
            for task in cat_tasks:
                due_display = self._format_due_date(task)
                values = (
                    task.get('name', ''),
                    '',  # Don't repeat category
                    task.get('importance', ''),
                    due_display,
                    f"{task.get('progress', 0)}%"
                )
                self.task_tree.insert(group_id, 'end', iid=task['id'], values=values,
                                     tags=(task.get('importance', 'Medium'),))

    def _update_category_overview(self):
        """Update the category overview panel"""
        all_tasks = self.data_manager.get_tasks()

        # Calculate stats per category
        cat_stats = {}
        for cat in self.CLASSIFICATIONS:
            cat_stats[cat] = {'total': 0, 'progress_sum': 0, 'critical': 0, 'overdue': 0}

        today = datetime.now().date()
        for task in all_tasks:
            cat = task.get('classification', 'Other')
            if cat not in cat_stats:
                cat_stats[cat] = {'total': 0, 'progress_sum': 0, 'critical': 0, 'overdue': 0}

            cat_stats[cat]['total'] += 1
            cat_stats[cat]['progress_sum'] += task.get('progress', 0)

            if task.get('importance') == 'Critical':
                cat_stats[cat]['critical'] += 1

            # Check overdue
            if task.get('due_type') == 'specific_date' and task.get('due_date'):
                try:
                    due = datetime.fromisoformat(task['due_date']).date()
                    if due < today:
                        cat_stats[cat]['overdue'] += 1
                except (ValueError, TypeError):
                    pass

        # Build overview text
        overview_lines = []
        overview_lines.append("=" * 23)
        overview_lines.append("  CATEGORY OVERVIEW")
        overview_lines.append("=" * 23)
        overview_lines.append("")

        total_all = 0
        for cat in self.CLASSIFICATIONS:
            stats = cat_stats[cat]
            if stats['total'] == 0:
                continue

            total_all += stats['total']
            avg = stats['progress_sum'] // stats['total'] if stats['total'] > 0 else 0

            # Category name (shortened)
            short_cat = cat.replace(' Goals', '').replace(' ', '')[:12]
            overview_lines.append(f"{short_cat}:")
            overview_lines.append(f"  Tasks: {stats['total']}")
            overview_lines.append(f"  Progress: {avg}%")

            if stats['critical'] > 0:
                overview_lines.append(f"  Critical: {stats['critical']}")
            if stats['overdue'] > 0:
                overview_lines.append(f"  Overdue: {stats['overdue']}")

            # Progress bar (clamp to 0-100)
            clamped_avg = max(0, min(100, avg))
            filled = clamped_avg // 10
            bar = "[" + "#" * filled + "-" * (10 - filled) + "]"
            overview_lines.append(f"  {bar}")
            overview_lines.append("")

        overview_lines.append("-" * 23)
        overview_lines.append(f"Total Active: {total_all}")

        # Update text widget
        self.category_overview.config(state='normal')
        self.category_overview.delete('1.0', tk.END)
        self.category_overview.insert('1.0', '\n'.join(overview_lines))
        self.category_overview.config(state='disabled')

    def _update_filter_button_counts(self):
        """Update quick filter buttons with task counts"""
        all_tasks = self.data_manager.get_tasks()

        # Count tasks per category
        cat_counts = {"All": len(all_tasks)}
        for cat in self.CLASSIFICATIONS:
            cat_counts[cat] = 0

        for task in all_tasks:
            cat = task.get('classification', 'Other')
            if cat in cat_counts:
                cat_counts[cat] += 1

        # Update button text
        if "All" in self.category_buttons:
            self.category_buttons["All"].config(text=f"All ({cat_counts['All']})")

        for cat in self.CLASSIFICATIONS:
            if cat in self.category_buttons:
                short_name = cat.split()[0][:4]
                if cat_counts[cat] > 0:
                    self.category_buttons[cat].config(text=f"{short_name}({cat_counts[cat]})")
                else:
                    # Reset to just short name when no tasks
                    self.category_buttons[cat].config(text=short_name)

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
        # Ignore double-click on group headers
        item = self.task_tree.identify_row(event.y)
        if item and item.startswith('_group_'):
            return
        self._edit_selected_task()

    def _show_task_context_menu(self, event):
        """Show context menu for tasks"""
        item = self.task_tree.identify_row(event.y)
        if item and not item.startswith('_group_'):
            self.task_tree.selection_set(item)
            self.task_context_menu.tk_popup(event.x_root, event.y_root)

    def _get_selected_task(self, silent: bool = False) -> Optional[Dict]:
        """Get currently selected task

        Args:
            silent: If True, don't show message dialogs for errors
        """
        selection = self.task_tree.selection()
        if not selection:
            if not silent:
                messagebox.showinfo("Info", "Please select a task first")
            return None

        task_id = selection[0]
        # Ignore group headers
        if task_id.startswith('_group_'):
            if not silent:
                messagebox.showinfo("Info", "Please select a task, not a category header")
            return None

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

        task_name = task.get('name', 'Task')
        display_name = task_name[:40] + "..." if len(task_name) > 40 else task_name
        ttk.Label(frame, text=f"Progress for: {display_name}").pack()

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
        # Find the idea without removing it yet
        idea = None
        for item in self.data_manager.get_backtrack():
            if item['id'] == idea_id:
                idea = item
                break

        if idea:
            # Create task directly with pre-filled data from idea
            # Store the idea ID so we can delete it after successful save
            task_data = {
                'name': idea.get('text', ''),
                'classification': idea.get('classification', 'Other'),
                'notes': idea.get('notes', ''),
                'importance': 'Medium',
                'due_type': 'none',
                'due_date': None,
                'progress': 0,
                'recurring': False,
                'status': 'active',
                '__promote_id__': idea_id  # Track which idea to delete on save
            }
            # Pass to dialog - idea will be deleted only when Save is clicked
            self._show_add_task_dialog_prefilled(task_data)

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
            if self.data_manager.export_to_csv(filename):
                messagebox.showinfo("Success", f"Tasks exported to {filename}")

    def _show_statistics_dialog(self):
        """Show statistics in a dialog"""
        self.notebook.select(self.stats_frame)

    def _show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About Personal Task Tracker",
            "Personal Task Tracker v2.0\n\n"
            "A comprehensive task management application\n\n"
            "Features:\n"
            "- Task management with priorities & categories\n"
            "- Progress tracking & streaks\n"
            "- Backtrack ideas storage\n"
            "- Statistics dashboard\n"
            "- Pomodoro Timer for focus\n"
            "- Dark/Light theme\n"
            "- Import/Export CSV\n"
            "- Backup & Restore\n"
            "- Task snoozing & duplication\n"
            "- Daily review summary"
        )

    def _show_shortcuts(self):
        """Show keyboard shortcuts"""
        messagebox.showinfo("Keyboard Shortcuts",
            "Keyboard Shortcuts:\n\n"
            "Ctrl+N: New task\n"
            "Ctrl+Shift+N: Quick add task\n"
            "Delete: Delete selected item\n"
            "Double-click: Edit task\n"
            "Right-click: Context menu\n\n"
            "Pomodoro Timer:\n"
            "Space: Start/Pause\n"
            "R: Reset timer"
        )

    def _on_close(self):
        """Handle window close"""
        self.data_manager.save_data()
        self.destroy()

    # ========================================================================
    # New Features
    # ========================================================================

    def _apply_theme(self):
        """Apply the current theme to the application"""
        theme = self.THEMES.get(self.current_theme, self.THEMES['light'])

        # Configure main window
        self.configure(bg=theme['frame_bg'])

        # Update ttk styles for theme
        style = ttk.Style()

        if self.current_theme == 'dark':
            style.configure('TFrame', background=theme['frame_bg'])
            style.configure('TLabel', background=theme['frame_bg'], foreground=theme['fg'])
            style.configure('TLabelframe', background=theme['frame_bg'])
            style.configure('TLabelframe.Label', background=theme['frame_bg'], foreground=theme['fg'])
            style.configure('TNotebook', background=theme['frame_bg'])
            style.configure('TNotebook.Tab', background=theme['bg'], foreground=theme['fg'])
            style.map('TNotebook.Tab', background=[('selected', theme['select_bg'])])

            # Configure Treeview
            style.configure('Treeview',
                          background=theme['tree_bg'],
                          foreground=theme['fg'],
                          fieldbackground=theme['tree_bg'])
            style.map('Treeview', background=[('selected', theme['select_bg'])])
        else:
            # Reset to light theme defaults
            style.configure('TFrame', background='')
            style.configure('TLabel', background='', foreground='')
            style.configure('TLabelframe', background='')
            style.configure('TLabelframe.Label', background='', foreground='')
            style.configure('Treeview', background='white', foreground='black',
                          fieldbackground='white')

    def _toggle_theme(self):
        """Toggle between light and dark theme"""
        self.current_theme = self.theme_var.get()
        self.data_manager.data['settings']['theme'] = self.current_theme
        self.data_manager.save_data()
        self._apply_theme()

    def _show_quick_add(self):
        """Show quick add dialog"""
        def on_save(task):
            self.data_manager.add_task(task)
            self._refresh_task_list()
            self._update_statistics()

        QuickAddDialog(self, self.CLASSIFICATIONS, on_save)

    def _duplicate_selected_task(self):
        """Duplicate the selected task"""
        task = self._get_selected_task()
        if task:
            new_task = task.copy()
            new_task.pop('id', None)
            new_task.pop('created_at', None)
            new_task.pop('updated_at', None)
            new_task['name'] = f"Copy of {task['name']}"
            new_task['progress'] = 0
            self.data_manager.add_task(new_task)
            self._refresh_task_list()
            self._update_statistics()
            messagebox.showinfo("Success", "Task duplicated!")

    def _snooze_selected_task(self):
        """Snooze the selected task"""
        task = self._get_selected_task()
        if not task:
            return

        dialog = tk.Toplevel(self)
        dialog.title("Snooze Task")
        dialog.geometry("300x180")
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()

        # Center
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ttk.Frame(dialog, padding="20")
        frame.pack(fill='both', expand=True)

        task_name = task.get('name', 'Task')
        display_name = task_name[:30] + "..." if len(task_name) > 30 else task_name
        ttk.Label(frame, text=f"Snooze: {display_name}",
                 font=('Arial', 10, 'bold')).pack(pady=(0, 15))

        ttk.Label(frame, text="Postpone by:").pack()

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(pady=15)

        def snooze(days):
            self.data_manager.snooze_task(task['id'], days)
            dialog.destroy()
            self._refresh_task_list()
            messagebox.showinfo("Snoozed", f"Task snoozed by {days} day(s)")

        ttk.Button(btn_frame, text="1 Day", command=lambda: snooze(1), width=8).pack(side='left', padx=3)
        ttk.Button(btn_frame, text="3 Days", command=lambda: snooze(3), width=8).pack(side='left', padx=3)
        ttk.Button(btn_frame, text="1 Week", command=lambda: snooze(7), width=8).pack(side='left', padx=3)

        btn_frame2 = ttk.Frame(frame)
        btn_frame2.pack()
        ttk.Button(btn_frame2, text="2 Weeks", command=lambda: snooze(14), width=8).pack(side='left', padx=3)
        ttk.Button(btn_frame2, text="1 Month", command=lambda: snooze(30), width=8).pack(side='left', padx=3)
        ttk.Button(btn_frame2, text="Cancel", command=dialog.destroy, width=8).pack(side='left', padx=3)

    def _start_pomodoro(self):
        """Start a general Pomodoro timer"""
        PomodoroTimer(self, "Focus Session")

    def _focus_on_task(self):
        """Start Pomodoro timer for selected task"""
        task = self._get_selected_task()
        if task:
            def on_complete():
                # Increment progress by 10% per session
                current = task.get('progress', 0)
                new_progress = min(100, current + 10)
                self.data_manager.update_task(task['id'], {'progress': new_progress})
                self._refresh_task_list()

            PomodoroTimer(self, task.get('name', 'Task'), on_complete=on_complete)

    def _import_csv(self):
        """Import tasks from CSV"""
        filename = filedialog.askopenfilename(
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Import Tasks from CSV"
        )
        if filename:
            success, errors = self.data_manager.import_from_csv(filename)
            self._refresh_task_list()
            self._update_statistics()
            messagebox.showinfo("Import Complete",
                f"Imported {success} tasks successfully.\n"
                f"Errors: {errors}")

    def _create_backup(self):
        """Create a backup of all data"""
        backup_dir = filedialog.askdirectory(title="Select Backup Location")
        if backup_dir:
            backup_path = self.data_manager.create_backup(backup_dir)
            if backup_path:
                messagebox.showinfo("Backup Created", f"Backup saved to:\n{backup_path}")

    def _restore_backup(self):
        """Restore data from a backup"""
        if not messagebox.askyesno("Confirm Restore",
            "This will replace all current data with the backup.\n"
            "Are you sure you want to continue?"):
            return

        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Select Backup File"
        )
        if filename:
            if self.data_manager.restore_backup(filename):
                self._refresh_all()
                messagebox.showinfo("Restore Complete", "Data restored successfully!")

    def _show_daily_review(self):
        """Show daily review summary"""
        summary = self.data_manager.get_daily_summary()

        dialog = tk.Toplevel(self)
        dialog.title("Daily Review")
        dialog.geometry("500x450")
        dialog.resizable(True, True)
        dialog.transient(self)

        # Center
        dialog.update_idletasks()
        x = self.winfo_rootx() + (self.winfo_width() - dialog.winfo_width()) // 2
        y = self.winfo_rooty() + (self.winfo_height() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")

        main_frame = ttk.Frame(dialog, padding="20")
        main_frame.pack(fill='both', expand=True)

        # Header
        today = datetime.now().strftime("%A, %B %d, %Y")
        ttk.Label(main_frame, text=f"Daily Review - {today}",
                 font=('Arial', 14, 'bold')).pack(pady=(0, 15))

        # Create text widget for summary
        text = tk.Text(main_frame, wrap='word', font=('Arial', 10), height=20)
        scrollbar = ttk.Scrollbar(main_frame, command=text.yview)
        text.configure(yscrollcommand=scrollbar.set)

        text.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        # Build summary text
        content = []

        content.append("=" * 40)
        content.append("COMPLETED TODAY")
        content.append("=" * 40)
        if summary['completed_today']:
            for task in summary['completed_today']:
                content.append(f"  [DONE] {task.get('name', 'Unknown')}")
        else:
            content.append("  No tasks completed today yet.")
        content.append("")

        content.append("=" * 40)
        content.append("DUE TODAY")
        content.append("=" * 40)
        if summary['due_today']:
            for task in summary['due_today']:
                content.append(f"  [{task.get('importance', 'Medium')}] {task.get('name', 'Unknown')}")
        else:
            content.append("  No tasks due today.")
        content.append("")

        content.append("=" * 40)
        content.append("OVERDUE")
        content.append("=" * 40)
        if summary['overdue']:
            for task in summary['overdue']:
                content.append(f"  [!] {task.get('name', 'Unknown')}")
        else:
            content.append("  No overdue tasks!")
        content.append("")

        content.append("=" * 40)
        content.append("IN PROGRESS")
        content.append("=" * 40)
        if summary['in_progress']:
            for task in summary['in_progress']:
                content.append(f"  [{task.get('progress', 0)}%] {task.get('name', 'Unknown')}")
        else:
            content.append("  No tasks in progress.")

        text.insert('1.0', '\n'.join(content))
        text.configure(state='disabled')

        # Close button
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=15)


# ============================================================================
# Entry Point
# ============================================================================

def main():
    """Main entry point"""
    app = PersonalTracker()

    def handle_delete(event):
        """Handle delete key based on current tab"""
        current_tab = app.notebook.index(app.notebook.select())
        if current_tab == 0:  # Tasks tab
            # Use silent mode to avoid showing message when group header selected
            task = app._get_selected_task(silent=True)
            if task:
                if messagebox.askyesno("Confirm Delete", f"Delete task '{task['name']}'?"):
                    app.data_manager.delete_task(task['id'])
                    app._refresh_task_list()
                    app._update_statistics()
        elif current_tab == 1:  # Backtrack tab
            app._delete_backtrack_idea()

    # Bind keyboard shortcuts
    app.bind('<Control-n>', lambda e: app._show_add_task_dialog())
    app.bind('<Control-N>', lambda e: app._show_add_task_dialog())  # Caps lock support
    app.bind('<Control-Shift-n>', lambda e: app._show_quick_add())
    app.bind('<Control-Shift-N>', lambda e: app._show_quick_add())
    app.bind('<Delete>', handle_delete)
    app.bind('<F5>', lambda e: app._refresh_all())
    app.bind('<Control-d>', lambda e: app._duplicate_selected_task())
    app.bind('<Control-p>', lambda e: app._start_pomodoro())

    app.mainloop()


if __name__ == "__main__":
    main()

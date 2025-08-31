import argparse
import csv
import importlib
import os
import sys
import time
import typing
from datetime import datetime, timedelta

from selenium import webdriver
from selenium.webdriver.common.by import By

from entities import LogDay, LogPeriod


class LogDataService:
    def __init__(self):
        self._sanecum_username = os.environ.get("SANECUM_USERNAME", "")
        self._sanecum_password = os.environ.get("SANECUM_PASSWORD", "")
        self._redmine_username = os.environ.get("REDMINE_USERNAME", "")
        self._redmine_password = os.environ.get("REDMINE_PASSWORD", "")
        chrome_options = webdriver.ChromeOptions()
        chrome_options.add_argument("start-maximized")
        self.driver = webdriver.Remote("http://selenium:4444/wd/hub", options=chrome_options)

    def _sanecum_login(self, username, password):
        self.driver.find_element(By.NAME, "username").send_keys(username)
        self.driver.find_element(By.NAME, "password").send_keys(password)
        self.driver.find_element(By.ID, "kc-form-login").submit()

    def _kimai_add(self, begin_date: str, begin_time: str, end_time: str, description: str):
        time.sleep(2)
        self.driver.find_element(By.CLASS_NAME, "action-create").click()
        time.sleep(2)

        print("Adding...", begin_date, begin_time, end_time, description)
        inp_begin_data = self.driver.find_element(By.ID, "timesheet_edit_form_begin_date")
        inp_begin_data.clear()
        inp_begin_data.send_keys(begin_date)

        inp_begin_time = self.driver.find_element(By.ID, "timesheet_edit_form_begin_time")
        inp_begin_time.clear()
        inp_begin_time.send_keys(begin_time)

        inp_end_time = self.driver.find_element(By.ID, "timesheet_edit_form_end_time")
        inp_end_time.clear()
        inp_end_time.send_keys(end_time)

        row_project = self.driver.find_element(By.CLASS_NAME, "timesheet_edit_form_row_project")
        select_project = row_project.find_element(By.CLASS_NAME, "col-sm-10")
        select_project.click()
        time.sleep(1)
        option = self.driver.find_element(By.XPATH, '//div[text()="PE113.0002_SSM2"]')
        option.click()
        time.sleep(1)

        row_activity = self.driver.find_element(By.CLASS_NAME, "timesheet_edit_form_row_activity")
        select_activity = row_activity.find_element(By.CLASS_NAME, "col-sm-10")
        select_activity.click()
        time.sleep(1)
        option = self.driver.find_element(By.XPATH, '//div[text()="DEV-NS"]')
        option.click()

        inp_description = self.driver.find_element(By.ID, "timesheet_edit_form_description")
        inp_description.clear()
        inp_description.send_keys(description)

        row_tags = self.driver.find_element(By.CLASS_NAME, "timesheet_edit_form_row_tags")
        select_tags = row_tags.find_element(By.CLASS_NAME, "col-sm-10")
        select_tags.click()
        time.sleep(1)
        option = self.driver.find_element(By.XPATH, '//div[text()="SSM/Development"]')
        self.driver.execute_script("arguments[0].scrollIntoView(true);", option)
        time.sleep(2)
        option.click()
        select_tags.click()

        form = self.driver.find_element(By.NAME, "timesheet_edit_form")
        form.submit()

    def do_kimai(self, data: typing.Iterable[LogDay], format_date, format_time):
        self.driver.get("https://tracker.sanecum.io")
        button_login = self.driver.find_element(By.ID, "social-login-button")
        button_login.click()
        self._sanecum_login(self._sanecum_username, self._sanecum_password)

        for log_day_item in data:
            for log_period in log_day_item.items:
                self._kimai_add(
                    begin_date=log_period.start.strftime(format_date),
                    begin_time=log_period.start.strftime(format_time),
                    end_time=log_period.end.strftime(format_time),
                    description=log_period.description,
                )

        time.sleep(5)

    def _redmine_add(
        self, task_id: str, begin_date: datetime, begin_time: str, end_time: str, description: str, show_task=False
    ):
        print("Adding...", task_id, begin_date, begin_time, end_time, description)

        begin_time = datetime.strptime(begin_time, "%H:%M")
        end_time = datetime.strptime(end_time, "%H:%M")
        duration = end_time - begin_time
        hours = ":".join(str(duration).split(":")[:2])
        date_str = begin_date.strftime("%m%d%Y")

        if show_task:
            self.driver.get("https://red.backstage.pm/issues/%s" % task_id)
            task_title = self.driver.find_element(By.CLASS_NAME, "subject").find_element(By.TAG_NAME, "h3").text
            print("\tto #%s: %s" % (task_id, task_title))
        else:
            self.driver.get("https://red.backstage.pm/issues/%s/time_entries/new" % task_id)
            self.driver.find_element(By.ID, "time_entry_spent_on").send_keys(date_str)
            self.driver.find_element(By.ID, "time_entry_hours").send_keys(hours)
            self.driver.find_element(By.ID, "time_entry_comments").send_keys(description)

            self.driver.find_element(By.ID, "new_time_entry").submit()
            time.sleep(1)

    def do_redmine(self, data: typing.Iterable[LogDay], show_task: bool = False):
        self.driver.get("https://red.backstage.pm/")
        self.driver.find_element(By.ID, "username").send_keys(self._redmine_username)
        self.driver.find_element(By.ID, "password").send_keys(self._redmine_password)
        form_container = self.driver.find_element(By.ID, "login-form")
        form_container.find_element(By.TAG_NAME, "form").submit()
        time.sleep(2)

        code = input("Two-factor authentication code: ")

        self.driver.find_element(By.NAME, "twofa_code").send_keys(code.strip())
        self.driver.find_element(By.ID, "twofa_form").submit()
        time.sleep(2)

        for log_day_item in data:
            for log_period in log_day_item.items:
                self._redmine_add(
                    task_id=log_period.task_id,
                    begin_date=log_period.start,
                    begin_time=log_period.start.strftime("%H:%M"),
                    end_time=log_period.end.strftime("%H:%M"),
                    description=log_period.description,
                    show_task=show_task,
                )

    def close(self):
        self.driver.close()
        self.driver.quit()


def python_import_data(module_path: str) -> typing.Iterable[LogDay]:
    *module_parts, var_name = module_path.split(".")
    module_path = ".".join(module_parts)

    module = importlib.import_module(module_path)
    return getattr(module, var_name)


def csv_import_data(path: str) -> typing.Iterable[LogDay]:
    out_time_format = "%H:%M"
    out_date_format = "%d.%m.%Y"
    with open(path) as csvfile:
        reader = csv.DictReader(csvfile)
        current_log_day = None
        for row in reader:
            date_str = row["date"]
            date = datetime.strptime(date_str, "%d.%m.%Y")
            if not current_log_day or date.date() != current_log_day.date:
                if current_log_day:
                    yield current_log_day
                current_log_day = LogDay(
                    date=datetime.strftime(date, out_date_format),
                    items=[],
                )
            time_start_str = row["start"]
            time_end_str = row["end"]
            time_start = datetime.strptime(time_start_str, "%H:%M")
            time_end = datetime.strptime(time_end_str, "%H:%M")

            log_period = LogPeriod(
                start=datetime.strftime(time_start, out_time_format),
                end=datetime.strftime(time_end, out_time_format),
                description=row["description"],
            )
            log_period.set_date(date=date.date())
            current_log_day.items.append(log_period)

        if current_log_day:
            yield current_log_day


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example script with parameters")
    parser.add_argument("--format", type=str, required=True, help="Input data type")
    parser.add_argument("--platform", type=str, required=True, help="Show parsed data only")
    parser.add_argument("--src", type=str, required=True, help="Data source path")
    parser.add_argument("--show_only", action="store_true", help="Show parsed data only")
    parser.add_argument("--show_task", action="store_true", help="Show task from description")
    args = parser.parse_args()

    # logging.basicConfig()
    # logging.getLogger().setLevel(logging.DEBUG)

    match str(args.format):
        case "csv":
            time_log_data = csv_import_data(args.src)
        case "py":
            time_log_data = python_import_data(args.src)
        case _:
            sys.exit("Invalid data format")

    if args.show_only:
        total_duration = timedelta()
        for log_day in time_log_data:
            print(log_day.date, log_day.total_duration())
            for log_item in log_day.items:
                item_duration = log_item.get_duration()
                print(
                    "\t %s-%s - %s %s"
                    % (
                        log_item.start.strftime("%H:%M"),
                        log_item.end.strftime("%H:%M"),
                        item_duration,
                        log_item.description,
                    )
                )
                total_duration += log_item.get_duration()
        total_hours = int(total_duration.total_seconds() // 3600)
        total_minutes = int((total_duration.total_seconds() % 3600) // 60)
        print("Total: {total_hours} h {total_minutes} m".format(total_hours=total_hours, total_minutes=total_minutes))
        sys.exit(0)

    log_data_service = LogDataService()

    try:
        match str(args.platform):
            case "kimai":
                date_format = "%d.%m.%Y"
                time_format = "%H:%M"
                # date_format = "%m/%d/%Y"
                # time_format = "%I:%M %p"
                log_data_service.do_kimai(time_log_data, format_date=date_format, format_time=time_format)
            case "redmine":
                log_data_service.do_redmine(time_log_data, args.show_task)
            case _:
                sys.exit("Invalid data platform")
    finally:
        log_data_service.close()

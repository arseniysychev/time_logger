import argparse
import csv
import importlib
import os
import sys
import time
import typing
from datetime import datetime

from selenium import webdriver
from selenium.webdriver.common.by import By

from entities import LogDay, LogPeriod


class LogDataService:
    def __init__(self):
        self._sanecum_username = os.environ.get("SANECUM_USERNAME", "")
        self._sanecum_password = os.environ.get("SANECUM_PASSWORD", "")
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

        form = self.driver.find_element(By.NAME, "timesheet_edit_form")
        form.submit()

    def do_kimai(self, data: typing.Iterable[LogDay]):
        self.driver.get("https://tracker.sanecum.io")
        button_login = self.driver.find_element(By.ID, "social-login-button")
        button_login.click()
        self._sanecum_login(self._sanecum_username, self._sanecum_password)

        for log_day_item in data:
            for log_period in log_day_item.items:
                self._kimai_add(
                    begin_date=(
                        log_day_item.date if log_day_item.date.endswith(".2025") else log_day_item.date + ".2025"
                    ),
                    begin_time=log_period.start,
                    end_time=log_period.end,
                    description=log_period.description,
                )

        time.sleep(5)

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
            date_str = row["Datum"]
            date = datetime.strptime(date_str, "%d.%m.%Y")
            if not current_log_day or date_str != current_log_day.date:
                if current_log_day:
                    yield current_log_day
                current_log_day = LogDay(
                    date=datetime.strftime(date, out_date_format),
                    items=[],
                )
            time_start_str = row["Arbeitszeit von "]
            time_end_str = row["Arbeitszeit bis"]
            time_start = datetime.strptime(time_start_str, "%H:%M")
            time_end = datetime.strptime(time_end_str, "%H:%M")

            current_log_day.items.append(
                LogPeriod(
                    start=datetime.strftime(time_start, out_time_format),
                    end=datetime.strftime(time_end, out_time_format),
                    description=row["Beschreibung"],
                )
            )

        if current_log_day:
            yield current_log_day


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Example script with parameters")
    parser.add_argument("--format", type=str, required=True, help="Input data type")
    parser.add_argument("--src", type=str, required=True, help="Data source path")
    parser.add_argument("--show_only", action="store_true", help="Show parsed data only")
    args = parser.parse_args()

    match str(args.format):
        case "csv":
            time_log_data = csv_import_data(args.src)
        case "py":
            time_log_data = python_import_data(args.src)
        case _:
            sys.exit("Invalid data format")

    if args.show_only:
        for log_day in time_log_data:
            print(log_day.date)
            for log_item in log_day.items:
                print("\t %s-%s %s" % (log_item.start, log_item.end, log_item.description))
        sys.exit(0)

    log_data_service = LogDataService()

    try:
        log_data_service.do_kimai(time_log_data)
    finally:
        log_data_service.close()

import requests
from datetime import date, timedelta
from bs4 import BeautifulSoup
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import logging
# use your own email and password
from secret import my_email, password, receivers

logging.basicConfig(filename='script.log', level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s', filemode='a')

def get_date() -> tuple:
    """Gets today's date and retuns today's date
    and date 30 days from now as a tuple."""
    from_today = date.today()
    until_date = from_today + timedelta(days=30)

    str_from_today = from_today.strftime("%Y-%m-%d")
    str_until_date = until_date.strftime("%Y-%m-%d")
    return str_from_today, str_until_date


def get_description(link) -> str:
    """Looks for an event description on an event webpage
    and returns it. This block of code covers most of the cases
    of how HTML of the page is written. If no description is found,
    it returns an empty string."""
    source = requests.get(link)
    if source.status_code == 200:
        soup = BeautifulSoup(source.content, "html.parser")
        try:
            divs_with_class = soup.select('div[class*="b-content__annot"]')
            for div in divs_with_class:
                strong_element = div.find("strong")
                p = div.find("p")
                if strong_element:
                    strong_text = strong_element.text
                    return strong_text
                if p:
                    if p.find("span"):
                        span = p.find("span")
                        return span.text
                    if p.text:
                        return p.text

            p_with_class = soup.select('p[class*="b-content__annot"]')
            for p in p_with_class:
                if p.find("strong"):
                    return p.find("strong").text
                if p.find("span"):
                    return p.find("span").text
       
            return ""
        except Exception as e:
            logging.error(f"Error is {e}")
    return ""


def scrape_events(category, unique_names, my_events):
    """Scrapes website in a given period of time for events of chosen category. 
    To avoid duplicates it checks duplicity using set(). It saves
    the events in a dictionary using keys: name, date, link and description."""
    params = {
        "cat": category
    }
    from_date, until_date = get_date()
    URL = f"https://www.gotobrno.cz/kalendar-akci/?date={from_date}%2C{until_date}&type=grid"

    source = requests.get(URL, params)
    logging.info(f"Connection: {URL}{params} - {source.status_code}")

    soup = BeautifulSoup(source.content, "html.parser")
    results = soup.find_all("li", class_="grid__cell size--t-4-12 c-grid__item")

    for result in results:
        link = result.find("a", href=True)["href"].strip()
        description = get_description(link).replace("\xa0", " ")

        div = result.find(class_="b-image__content")
        h = div.find("h3").text.strip().replace("\xa0", " ")
        p = div.find("p").text.strip()
        

        if h not in unique_names:
            my_events.append({"name": h, "date": p, "link": link, "description": description})
            # print(f"{h}: {p}; {link}, {description}")
        unique_names.add(h)


def save_as_json(my_events: dict):
    """Saves scraped events as JSON file."""
    json_object = json.dumps(my_events, indent= 4)
    with open("events.json", "w", encoding="utf-8") as f:
        f.write(json_object)


def send_email(my_events: dict):
    """Sends e-mail to all receivers with planned events using
    HTML-based template."""
    html_message = """
    <html>
    <head>
    <style>
    .event {
        background-color: red;
        color: white;
        font-family: sans-serif;
        padding: 10px;
        margin: 10px;
    }
    a {
        color: white;

    }
    </style>
    </head>
    <body>
    """

    for event in my_events:
        event_div = f"""
            <div class="event"><strong>{event["name"]}</strong><br>
                <p>{event["date"]}</p>
                <a href="{event["link"]}"> >> odkaz << </a>
                <p>{event["description"]}</p>
            </div>"""
        html_message += event_div

    html_message += """
    </body>
    </html>
    """



    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = my_email
    msg['To'] = my_email
    msg['Subject'] = "Přehled brněnských akcí"

    # Attach the HTML message
    msg.attach(MIMEText(html_message, 'html'))

    with smtplib.SMTP("smtp.gmail.com") as connection:
        connection.starttls() # secured connection
        connection.login(user=my_email, password=password)
        connection.sendmail(
            from_addr=my_email, 
            to_addrs=receivers,
            msg=msg.as_string()
        )
        logging.info("Emails were sent SUCCESSFULLY.")


# event categories to be scraped
categories = ["festivaly", "vystava", "gastronomicke", "veletrhy-vzdelavaci", "akce-tic-brno"]

unique_names = set()
my_events = list()



for category in categories:
    scrape_events(category, unique_names, my_events)

save_as_json(my_events)
send_email(my_events)



from bs4 import BeautifulSoup as Bs
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
import requests
from gender import getGenders
COLNAMES = ["Name", "Jobbezeichnung", "SFB_Arbeitsanteil", "Zuständiger_PL"]
GENDERCOLS = ["Geschlecht", "Geschl_Proba"]
link = "./TU Dortmund -- SFB876.html"
ARBEITSANTEIL = "Arbeitsanteil:"
PERCENT = "Prozent_Arbeitszeit"
CONTRACTGENCOLS = ["Gesamtdauer_Kumulativ / M", "Anzahl_Verträge"]
CONTRACTLOOPCOLS = [["Vertrag_1_Dauer / M", "Vertrag_1_Start", "Vertrag_1_Ende"],
                    ["Vertrag_2_Dauer / M", "Vertrag_2_Start", "Vertrag_2_Ende"],
                    ["Vertrag_3_Dauer / M", "Vertrag_3_Start", "Vertrag_3_Ende"],
                    ["Vertrag_4_Dauer / M", "Vertrag_4_Start", "Vertrag_4_Ende"],
                    ["Vertrag_5_Dauer / M", "Vertrag_5_Start", "Vertrag_5_Ende"]]
ARBEITSZEITKONST = 40.0 # number of hours worked equivalent to 100%
SFBGREEN = "#90ee90"
FILENMAE = "./TU Dortmund -- SFB876.html"

def get_scraped_page(url):
    return Bs(url, 'lxml')


def process_people(current_doms):
    active_names = current_doms.find_all('span', attrs={'class': ['nameactive']})
    inactive_names = current_doms.find_all('span', attrs={'class': ["nameinactive"]})
    return active_names, inactive_names


def process_arbeitsanteil(ateil):
    if isinstance(ateil, float):
        return "NaN"
    ateil = ateil.split("(")[0].strip()
    if "%" in ateil:
        ateil = ateil.split("%")[0].strip()
        return ateil+"%"
    else:
        if "h" in ateil:
            ateil = ateil.split("h")[0].strip()
            return str(ateil)+"h"
        else:
            ateil = ateil.strip()
            return str(ateil)+"h?"


def get_times_worked_in_hours_from_str(strings):
    pass


def get_times_worked_in_percent(strings):

    def get_percent(string):
        if string == "NaN":
            return np.nan
        string = string.replace(",", ".")
        if "%" in string:
            return float(string.replace("%", "").strip())
        elif "h" not in string:
            return np.nan
        elif "h" in string:
            if "?" in string:
                time = float(string.replace("h?", "").strip())
            else:
                time = float(string.replace("h", "").strip())
            return time/ARBEITSZEITKONST

    percentages = []
    for string in strings:
        percentages.append(get_percent(string))
    return percentages


def get_job_and_arbeitsanteil(jobtext):
    if ARBEITSANTEIL in jobtext:
        arbeitsanteil = jobtext.split(ARBEITSANTEIL)[1].strip()
    else:
        arbeitsanteil = np.nan
    if ("," in jobtext):
        if (ARBEITSANTEIL not in jobtext):
            print(jobtext)
            print("idk what to do")
            job = np.nan
        else:
            job = jobtext.split(",")[0].strip()
    elif "," not in jobtext:
        job = jobtext.split(",")[0].strip()
    else:
        job = np.nan

    arbeitsanteil = process_arbeitsanteil(arbeitsanteil)

    return arbeitsanteil, job


def get_projekleiter(text):
    pl = text.split("PL:")[-1].strip()
    if not pl:
        return "NaN"
    else:
        return pl


def handle_persontext(text):
    text.split("[]")
    name = text.split("[")[0].strip()
    pl = get_projekleiter(text)
    jobtext = text.split("[")[1].split("]")[0].strip()
    arbeitsanteil, job = get_job_and_arbeitsanteil(jobtext)

    return name, job, arbeitsanteil, pl  ### order the return values according to the COLNAMES


def get_firstname(fullname):
    fullname = fullname.strip()
    if " " in fullname:
        firstname = fullname.split(" ")[0]
    else:
        firstname = fullname
    return firstname


def _get_genders(df):
    genTuples = []
    for fullname in df["Name"].values:
        firstname = get_firstname(fullname)
        genTuple = getGenders(firstname)[0]
        genTuples.append(genTuple)
    genders = [gen[0] if gen is not None else "n" for gen, _,_ in genTuples]
    gender_probas = [genpro for _, genpro,_ in genTuples]

    return genders, gender_probas


def get_cont_durs_from_rects(rects):
    #contract_durs = []
    #prevmonth = None
    #for rect in rects:
    #    if rect.next.text != prevmonth
    pass


def get_contract_durations_from_svg(dom, color=SFBGREEN):
    test = dom.parent.parent.parent.find_all("div", attrs = {"class":["rcanvas_2"]})
    svg = test.find_all("svg")[0]
    rects = svgs.find_all("rect", attrs={"fill": [color]})
    contract_durs = get_cont_durs_from_rects(rects)
    cum_contract_dur = len(sfbrects)


def handle_employment(empl):
    text = " ".join(empl.text.split())
    if "SFB-Mittel:" in text:
        contract_dates = text.strip().split("SFB-Mittel:")[1].strip()
        start = contract_dates.split("-")[0].strip()
        end = contract_dates.split("-")[1].strip()
    else:
        start = np.nan
        end = np.nan

    return start, end


def get_contract_stats(persons):
    contracts = []
    for person in persons:
        employments = person.parent.parent.parent.find_all("span", attrs={"class":["employments"]})
        cutoff = 5
        assert len(employments) <= cutoff, f"too many employments, table has to be adjusted len: {len(employments)}"
        starts = []
        ends = []
        for empl in employments:
            start, end = handle_employment(empl)
            starts.append(start)
            ends.append(end)
        if cutoff - len(employments) > 0:
            for i in range(cutoff - len(employments)):
                starts.append(np.nan)
                ends.append(np.nan)

        starts = pd.to_datetime(starts, dayfirst=True)
        ends = pd.to_datetime(ends, dayfirst=True)
        tdeltas = ends - starts
        durations = tdeltas.days/30.
        contracts.append([durations, starts, ends]) ### watch order of columns

    return contracts


def assign_contract_cols(df, contracts):
    for i,CONTRACT in enumerate(CONTRACTLOOPCOLS):
        for j,col in enumerate(CONTRACT):
            df[col] = [contract[j][i] for contract in contracts]
    dur_cols = [contr[0] for contr in CONTRACTLOOPCOLS]
    df[CONTRACTGENCOLS[0]] = df[dur_cols].sum(axis=1, skipna=True)
    df[CONTRACTGENCOLS[1]] = df[dur_cols].apply(sum_contracts, axis=1)
    return df


def sum_contracts(contract_durs):
    i = 0
    for dur in contract_durs:
        if not np.isnan(dur):
            i += 1

    return i


def get_df_from_span(people, get_genders=False):
    peopleArr = [people.pop() for i in range(len(people))]
    textList = [" ".join(person.text.split()) for person in peopleArr]
    contracts = get_contract_stats(peopleArr)

    rows = []
    for text in textList:
        rows.append(handle_persontext(text))
    df = pd.DataFrame(columns=COLNAMES, data=rows)

    for col in GENDERCOLS:
        df[col] = "NaN"

    if get_genders is True:
        genders, gender_probas = _get_genders(df)
        df[GENDERCOLS[0]] = genders
        df[GENDERCOLS[1]] = gender_probas

    df[PERCENT] = get_times_worked_in_percent(df["SFB_Arbeitsanteil"].values)
    df = assign_contract_cols(df, contracts)

    return df


if __name__ == "__Main__":
    file = open(FILENAME, "r")
    current_doms = get_scraped_page(file)
    active_people, inactive_people = process_people(current_doms)
    active_df = get_df_from_span(active_people, get_genders=True)
    inactive_df = get_df_from_span(inactive_people, get_genders=True)

    active_df.to_csv("active_members.csv")
    inactive_df.to_csv("inactive_members.csv")

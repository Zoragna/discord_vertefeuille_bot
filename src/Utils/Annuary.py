import openpyxl
import json


def init_databases(connection):
    cursor = connection.cursor()
    query = ""
    with open("src/build.sql") as stream:
        for line in stream:
            query += line
    print(query)
    cursor.execute(query, ())
    connection.commit()


def get_json(path):
    with open(path, "rb") as stream:
        return json.load(stream)


def storeAnnuary(path, **kwargs):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    if "characters" in kwargs:
        ws_chars = wb.create_sheet(title="Personnages")

        ws_chars[openpyxl.utils.get_column_letter(2) + "1"] = "Nom"
        ws_chars[openpyxl.utils.get_column_letter(3) + "1"] = "Classe"
        ws_chars[openpyxl.utils.get_column_letter(4) + "1"] = "Couleur"
        ws_chars[openpyxl.utils.get_column_letter(5) + "1"] = "Niveau"

        i = 2
        for character in kwargs["characters"]:
            ws_chars[openpyxl.utils.get_column_letter(2) + str(i)] = character.name
            ws_chars[openpyxl.utils.get_column_letter(3) + str(i)] = character.class_
            color_cell = openpyxl.utils.get_column_letter(4) + str(i)
            ws_chars[color_cell] = character.main_trait
            if character.main_trait == "rouge":
                ws_chars[color_cell].font = openpyxl.styles.Font(color=openpyxl.styles.colors.RED, bold=True)
            elif character.main_trait == "bleu":
                ws_chars[color_cell].font = openpyxl.styles.Font(color=openpyxl.styles.colors.BLUE, bold=True)
            elif character.main_trait == "jaune":
                ws_chars[color_cell].font = openpyxl.styles.Font(color=openpyxl.styles.colors.YELLOW, bold=True)
            ws_chars[openpyxl.utils.get_column_letter(5) + str(i)] = character.level
            i += 1

    if "jobs" in kwargs:
        ws_jobs = wb.create_sheet(title="Métiers")

        ws_jobs[openpyxl.utils.get_column_letter(2) + "1"] = "Nom"
        ws_jobs[openpyxl.utils.get_column_letter(3) + "1"] = "Métier"
        ws_jobs[openpyxl.utils.get_column_letter(4) + "1"] = "Catégorie"
        ws_jobs[openpyxl.utils.get_column_letter(5) + "1"] = "Niveau"

        i = 2
        for job in kwargs["jobs"]:
            ws_jobs[openpyxl.utils.get_column_letter(2) + str(i)] = job["name"]
            ws_jobs[openpyxl.utils.get_column_letter(3) + str(i)] = job["job"]
            i += 1

    if "reps" in kwargs:
        ws_reps = wb.create_sheet(title="Réputations")

        ws_reps[openpyxl.utils.get_column_letter(2) + "1"] = "Nom"
        ws_reps[openpyxl.utils.get_column_letter(3) + "1"] = "Faction"
        ws_reps[openpyxl.utils.get_column_letter(4) + "1"] = "Niveau"
        ws_reps[openpyxl.utils.get_column_letter(5) + "1"] = "Points"

        i = 2
        for rep in kwargs["reps"]:
            ws_reps[openpyxl.utils.get_column_letter(2) + str(i)] = rep["char"]
            ws_reps[openpyxl.utils.get_column_letter(3) + str(i)] = rep["name"]
            ws_reps[openpyxl.utils.get_column_letter(4) + str(i)] = rep["level"]
            ws_reps[openpyxl.utils.get_column_letter(5) + str(i)] = rep["points"]
            i += 1

    if "anvils" in kwargs:
        ws_anvils = wb.create_sheet(title="Enclumes")
    try:
        wb.save(filename=path)
    except:
        print("Could not save annuary as xlsx")

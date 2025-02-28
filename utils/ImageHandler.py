import io

import pandas as pd
import matplotlib.pyplot as plt

from utils.Types import car_types


def format_time(time: int) -> str:
    minutes, seconds = divmod(time, 60000)
    seconds, ms = divmod(seconds, 1000)

    return f"{minutes:02}:{seconds:02}.{ms:03}"


columns = [
    "Pos.",
    "Driver Name",
    "Car Model",
    "Split 1",
    "Split 2",
    "Split 3",
    "Best Lap Time",
    "Theoretical Best",
    "Delta",
]


def format_data(data):
    unformatted_data = sorted(data.values(), key=lambda x: x["bestLap"], reverse=False)

    fastest_time = unformatted_data[0]["bestLap"]

    return [
        [
            pos,
            driver["name"],
            car_types[driver["car"]],
            f"{driver['bestSplits'][0] / 1000:.3f}",
            f"{driver['bestSplits'][1] / 1000:.3f}",
            f"{driver['bestSplits'][2] / 1000:.3f}",
            format_time(driver["bestLap"]),
            format_time(sum(driver["bestSplits"])),
            f"{(driver['bestLap'] - fastest_time) / 1000:.3f}",
        ]
        for pos, driver in enumerate(unformatted_data, 1)
    ]


def gen_image(data):
    """
    The styling of this table is pretty much copied from Noobs R Us Timings bot
    """
    fastest_splits = [1000000, 1000000, 1000000]

    for driver in data:
        for i in range(3, 6):
            if float(driver[i]) < fastest_splits[i - 3]:
                fastest_splits[i - 3] = float(driver[i])

    df = pd.DataFrame(data, columns=columns)

    fig, ax = plt.subplots(figsize=(12, 3))
    ax.axis("tight")
    ax.axis("off")

    col_widths = [0.05, 0.16, 0.22, 0.08, 0.08, 0.08, 0.12, 0.13, 0.05]

    table = ax.table(
        cellText=df.values,
        colLabels=df.columns,
        cellLoc="left",
        loc="center",
        colWidths=col_widths,
    )

    # Styling the table
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1.2, 1.2)

    for (i, j), cell in table.get_celld().items():
        if i == 0:  # Header
            cell.set_facecolor("#3D3D3D")
            cell.set_text_props(color="white")
        elif i == 1:  # First (Gold)
            cell.set_facecolor("#FFD700")
        elif i == 2:  # Second (Silver)
            cell.set_facecolor("#C0C0C0")
        elif i == 3:  # Third (Bronze)
            cell.set_facecolor("#CD7F32")

    for i in range(3, 6):
        for j in range(1, len(data) + 1):
            cell = table[j, i]
            if float(cell.get_text()._text) == fastest_splits[i - 3]:
                cell.set_facecolor("#9f0dc0")
                cell.set_text_props(color="white")

    image_stream = io.BytesIO()
    plt.savefig(image_stream, format="png", bbox_inches="tight")
    image_stream.seek(0)

    return image_stream

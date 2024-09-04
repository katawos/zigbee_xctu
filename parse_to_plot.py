import json
import csv
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, date, time, timedelta


def convertTimeStrToSeconds(str):
    time = datetime.strptime(str, "%H:%M:%S.%f").time()
    t = datetime.combine(date.min, time) - datetime.min
    t = t.total_seconds()
    return t


def scatter(ax, rest_df, name):
    # Init
    t = []
    psnr = []
    labels = []
    label_list = []

    for idx in range(rest_df.shape[0]):
        df = rest_df.iloc[idx]

        t.append(convertTimeStrToSeconds(df["t"]))
        psnr.append(df["PSNR"])

        label = df["Experiment"]
        label_list = label.split("_")
        labels.append(label_list[-1])
        # labels.append(label)

    # plotting the points
    ax.scatter(t, psnr, marker="x")

    # ax.set_xscale('log', nonpositive='clip')
    # ax.set_yscale('log', nonpositive='clip')

    # Get the current x-ticks
    current_xticks = ax.get_xticks()

    # Combine the current ticks with the additional ones
    all_xticks = sorted(set(current_xticks).union(t))

    # Set the combined x-ticks
    ax.set_xticks(all_xticks)
    ax.set_xticklabels([f"{i:.2f}" if i in t else str(i) for i in all_xticks])

    # Get the current x-ticks
    # current_yticks = ax.get_yticks()
    current_yticks = []

    # Combine the current ticks with the additional ones
    all_yticks = sorted(set(current_yticks).union(psnr))

    # Set the combined x-ticks
    ax.set_yticks(all_yticks)
    ax.set_yticklabels([f"{i:.2f}" if i in psnr else str(i) for i in all_yticks])

    for i, label in enumerate(labels):
        ax.annotate(label, (t[i] + 0.005, psnr[i]), fontsize=10)

    # naming the x axis
    ax.set_xlabel("time [s]")
    # naming the y axis
    ax.set_ylabel("psnr [dB]")

    # x_min, x_max = np.min(t), np.max(t)
    # # Set the x and y limits
    # ax.set_xlim(left = x_min, right = x_max)

    # giving a title to my graph
    ax.set_title(label_list[-2] + name)
    ax.grid()
    # ax.legend()


def json_to_plot(jsonl_file, showOriginal=True, figTitle="test"):
    file = open(jsonl_file, "r")
    lines = file.readlines()
    file.close()

    jsonl_file_list = jsonl_file.split(".")
    file_name = jsonl_file_list[0] + ".png"

    df = None

    for line in lines:
        first_line = line.replace("\n", "")
        first_line = first_line.replace("'", '"')
        json_data = json.loads(first_line)

        if df is None:
            df = pd.DataFrame.from_dict(pd.json_normalize(json_data), orient="columns")
        else:
            df2 = pd.DataFrame.from_dict(pd.json_normalize(json_data), orient="columns")
            df = pd.concat([df, df2], ignore_index=True)

    print(df.head(10))

    # Parse to matplotplib plot data structure
    original_time = df.iloc[0]["t"]
    original_time = convertTimeStrToSeconds(original_time)
    # rest_df = df.iloc[1:]

    rest_df = df[~df["Experiment"].str.contains("original")]

    # fig = plt.figure(layout="constrained", figsize=(9, 9))
    fig = plt.figure()
    fig.suptitle(figTitle, fontsize=12)

    df_methods_names = rest_df["Method"].unique()
    df_transmission_names = rest_df["transmission"].unique()

    subplots_num = len(df_methods_names) * len(df_transmission_names)

    idx = 1
    for method in df_methods_names:
        df_method = rest_df[rest_df["Method"] == method]

        for transmission in df_transmission_names:
            df_transmission = df_method[df_method["transmission"] == transmission]

            if df_transmission.size > 0:
                ax = fig.add_subplot(subplots_num, 1, idx)
                if showOriginal == True:
                    ax.set_xticks([original_time])
                    ax.set_xticklabels([f"{original_time:.2f}"])
                    ax.axvline(
                        original_time,
                        color="red",
                        linestyle="dashed",
                        linewidth=1,
                        label="original_time",
                    )  # original time
                else:
                    ax.set_xticks([])

                name = ""
                if method != "None":
                    name += "_" + str(method)
                if transmission != "None":
                    name += "_" + str(transmission)
                scatter(ax, df_transmission, name)
                idx += 1

    # function to show the plot
    # plt.show()
    fig.savefig(file_name)


# Example usage
# json_to_plot(
#     r"out\tests-28-08-2024\initial\payload\narrow\payload_test_narrow_range_2024-08-29_10-44-29\test_fix.txt",
#     r"out\tests-28-08-2024\initial\payload\narrow\payload_test_narrow_range_2024-08-29_10-44-29\test.png",
#     showOriginal=False,
#     figTitle="test",
# )

# json_to_plot(
#     r"out\tests-28-08-2024\initial\payload\wide\test.txt",
#     r"out\tests-28-08-2024\initial\payload\wide\test.png",
#     showOriginal=False,
#     figTitle="test",
# )

json_to_plot(
    r"out\tests-28-08-2024\final\differential images\diff_with_compr_Street_pix_diff_2024-08-28_20-23-37\test.txt",
    showOriginal=False,
    figTitle="test",
)

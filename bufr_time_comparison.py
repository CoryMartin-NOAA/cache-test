import ncepbufr
import numpy as np
from datetime import datetime
import sys

def compare_times(bufr_file):
    """
    Reads a BUFR file and compares the average time between receipt and observation time.
    Uses nceplibs-bufr (ncepbufr) Python wrapper.
    """
    try:
        bufr = ncepbufr.open(bufr_file)
    except Exception as e:
        print(f"Error opening BUFR file: {e}")
        return

    observation_times = []
    receipt_times = []

    print(f"Analyzing {bufr_file}...")

    while bufr.advance() == 0:
        # Radiosonde messages usually have types like NC002001, NC002002, NC002003, NC002004, NC002005
        # We'll check if the message type suggests radiosonde data (type 002)
        # or just try to extract the time mnemonics.

        # Get tank receipt time from message header
        # receipt_time is YYYYMMDDHHMM
        rt_val = bufr.receipt_time
        if rt_val == -1 or rt_val is None:
            continue

        rt_str = str(rt_val)
        try:
            rt = datetime.strptime(rt_str, '%Y%m%d%H%M')
        except ValueError:
            # Handle cases where the string might not be exactly 12 chars if leading zeros are missing
            # or other formatting issues.
            try:
                rt = datetime.strptime(rt_str.zfill(12), '%Y%m%d%H%M')
            except ValueError:
                continue

        while bufr.load_subset() == 0:
            # Mnemonics for observation time in radiosonde subsets
            # YEAR: Year
            # MNTH: Month
            # DAYS: Day
            # HOUR: Hour
            # MINU: Minute
            try:
                # read_subset returns a masked array (nm, nlevs)
                obs_time_data = bufr.read_subset('YEAR MNTH DAYS HOUR MINU')

                # We usually want the first level for the reference observation time
                if obs_time_data.shape[1] > 0:
                    year = int(obs_time_data[0, 0])
                    month = int(obs_time_data[1, 0])
                    day = int(obs_time_data[2, 0])
                    hour = int(obs_time_data[3, 0])
                    minute = int(obs_time_data[4, 0])

                    # Some BUFR files might have 2-digit years
                    if year < 100:
                        if year > 70:
                            year += 1900
                        else:
                            year += 2000

                    ot = datetime(year, month, day, hour, minute)

                    observation_times.append(ot)
                    receipt_times.append(rt)
            except Exception:
                # Skip subsets that don't have the required time mnemonics
                continue

    bufr.close()

    if not observation_times:
        print("No valid observations with both receipt and observation times found.")
        return

    # Calculate differences in minutes (Receipt Time - Observation Time)
    differences = [(r - o).total_seconds() / 60.0 for r, o in zip(receipt_times, observation_times)]

    avg_diff = np.mean(differences)
    min_diff = np.min(differences)
    max_diff = np.max(differences)
    std_diff = np.std(differences)

    print("\nResults:")
    print(f"Total observations processed: {len(observation_times)}")
    print(f"Average delay (Receipt - Observation): {avg_diff:.2f} minutes")
    print(f"Minimum delay: {min_diff:.2f} minutes")
    print(f"Maximum delay: {max_diff:.2f} minutes")
    print(f"Standard deviation: {std_diff:.2f} minutes")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python bufr_time_comparison.py <bufr_file>")
    else:
        compare_times(sys.argv[1])

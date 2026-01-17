import sys
from pylsl import StreamInlet, resolve_streams

def main():
    # 1. Look for active LSL streams
    print("Searching for streams...")
    streams = resolve_streams()

    if not streams:
        print("No streams found. Ensure your LSL source is active.")
        return

    # 2. List streams and let the user choose
    print("\nAvailable Streams:")
    for i, s in enumerate(streams):
        print(f"[{i}] Name: {s.name()} | Type: {s.type()} | Channels: {s.channel_count()} | Host: {s.hostname()}")

    try:
        choice = int(input("\nSelect stream index to print: "))
        selected_stream = streams[choice]
    except (ValueError, IndexError):
        print("Invalid selection. Exiting.")
        sys.exit(1)

    # 3. Create an inlet to receive data
    inlet = StreamInlet(selected_stream)

    print(f"\nPrinting data from {selected_stream.name()}... Press Ctrl+C to stop.\n")

    try:
        while True:
            # 4. Pull sample (sample is the data, timestamp is the LSL clock time)
            sample, timestamp = inlet.pull_sample()
            if sample:
                sample = sample[:2]
                avg=sum(sample)/len(sample)
                if avg<0.5:
                    avg=0.5
                avg = avg-0.5
                avg = avg*2
                print(f"TS: {timestamp:.1f} | Data: {avg:.1f}")
    except KeyboardInterrupt:
        print("\nStream stopped by user.")

if name == "main":
    main()
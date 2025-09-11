#!eval `which python3`
import re
import os
import sys
import signal
import time
import cv2
#import multiprocessing
import subprocess

from PIL import Image
from wakepy import keep

class SubtitleEntry:
    def __init__(self, index, start_time, end_time, text):
        self.index = index
        self.start_time = start_time  # in seconds
        self.end_time = end_time      # in seconds
        self.text = text.strip()

class SRTParser:
    def __init__(self, srt_path):
        self.srt_path = srt_path
        self.subtitles = []
        self.parse()
    
    def time_to_seconds(self, time_str):
        """Convert SRT time format (HH:MM:SS,mmm) to seconds"""
        time_str = time_str.replace(',', '.')  # Replace comma with dot for milliseconds
        parts = time_str.split(':')
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    
    def parse(self):
        """Parse SRT file and extract subtitle entries"""
        if not os.path.exists(self.srt_path):
            print(f"Warning: SRT file '{self.srt_path}' not found")
            return
        
        try:
            with open(self.srt_path, 'r', encoding='utf-8') as file:
                content = file.read().strip()
            
            # Split by double newlines to separate subtitle blocks
            blocks = re.split(r'\n\s*\n', content)
            
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    # Parse index
                    try:
                        index = int(lines[0])
                    except ValueError:
                        continue
                    
                    # Parse timing
                    timing_match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', lines[1])
                    if timing_match:
                        start_time = self.time_to_seconds(timing_match.group(1))
                        end_time = self.time_to_seconds(timing_match.group(2))
                        
                        # Join all remaining lines as subtitle text
                        text = '\n'.join(lines[2:])
                        
                        self.subtitles.append(SubtitleEntry(index, start_time, end_time, text))
        
        except Exception as e:
            print(f"Error parsing SRT file: {e}")
    
    def get_subtitle_at_time(self, current_time):
        """Get the subtitle that should be displayed at the given time"""
        for subtitle in self.subtitles:
            if subtitle.start_time <= current_time <= subtitle.end_time:
                return subtitle.text
        return None

class FrameBuffer:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.Buffer = []

    def store_frame(self,framedata):
        self.Buffer.append(framedata)
    def get_next_frame(self):
        return self.Buffer.pop(0)

def clear_screen():
    """Clear the terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def resize_frame(frame, width=80, height=24):
    """Resize frame to fit terminal dimensions"""
    # Convert OpenCV frame (BGR) to RGB
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Convert to PIL Image for easier resizing
    img = Image.fromarray(frame)
    img = img.resize((width, height), Image.BILINEAR)

    return img
def get_terminal_dimensions():
    """
    Returns the terminal's width in columns and height in lines.
    """
    try:
        size = os.get_terminal_size()
        return size.columns, size.lines
    except OSError:
        # Handle cases where the output is not connected to a TTY,
        # such as when piping output to a file or another command.
        # In such cases, you might want to provide a default size or
        # handle the error appropriately.
        return 80, 24  # Default to 80 columns and 24 lines
    
def rgb_to_ansi(r, g, b):
    """Convert RGB values to ANSI 256-color code"""
    # Convert to 6x6x6 color cube (216 colors)
    r_idx = int(r * 5 / 255)
    g_idx = int(g * 5 / 255)
    b_idx = int(b * 5 / 255)

    # ANSI 256-color formula: 16 + 36*r + 6*g + b
    color_code = 16 + 36 * r_idx + 6 * g_idx + b_idx
    return color_code

def image_to_ascii(image, use_color=False):
    """Convert PIL image to ASCII art with optional color support"""
    # Define ASCII characters from dark to light
    ascii_chars = "·¬°«+±¢®*º¤æ¾%§&¶@"
    if use_color:
        # Keep original image for color data
        color_image = image
        # Convert to grayscale for character selection
        gray_image = image.convert('L')
    else:
        # Convert image to grayscale
        gray_image = image.convert('L')
        color_image = None

    # Get pixel data
    gray_pixels = list(gray_image.getdata())

    if use_color:
        color_pixels = list(color_image.getdata())

    # Convert pixels to ASCII characters with bounds checking
    ascii_art = []

    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel_idx = y * image.width + x
            gray_value = gray_pixels[pixel_idx]

            # Fix the index out of bounds error by clamping the value
            char_idx = min(int(gray_value/9) , len(ascii_chars) - 1)
            char = ascii_chars[char_idx]

            if use_color and color_image:
                # Get RGB values for this pixel
                if len(color_pixels[pixel_idx]) >= 3:  # RGB or RGBA
                    r, g, b = color_pixels[pixel_idx][:3]
                    color_code = rgb_to_ansi(r, g, b)
                    # Apply ANSI color code
                    char = f"\033[38;5;{color_code}m{char}\033[0m"

            line += char

        ascii_art.append(line)

    return '\n'.join(ascii_art)

def image_to_ascii_blocks(image, use_color=False):
    """Convert PIL image to colored block ASCII art (alternative method)"""
    if not use_color:
        return image_to_ascii(image, use_color=False)

    # Use block characters for better color representation
    block_chars = "█▉▊▋▌▍▎▏ "

    # Get color pixels
    color_pixels = list(image.getdata())

    ascii_art = []

    for y in range(image.height):
        line = ""
        for x in range(image.width):
            pixel_idx = y * image.width + x

            if len(color_pixels[pixel_idx]) >= 3:  # RGB or RGBA
                r, g, b = color_pixels[pixel_idx][:3]

                # Calculate brightness for character selection
                brightness = int((r + g + b) / 3)
                char_idx = min(brightness // 25, len(block_chars) - 1)
                char = block_chars[char_idx]

                # Apply color
                color_code = rgb_to_ansi(r, g, b)
                char = f"\033[38;5;{color_code}m{char}\033[0m"
            else:
                char = " "

            line += char

        ascii_art.append(line)

    return '\n'.join(ascii_art)

def run_mpcmd(command):
    os.system(command)

def gettimer(seconds):
    secs = round(seconds % 60,2)
    minutes = int(seconds / (60))
    hours = int(seconds / (60*60))
    if secs < 10:
        secstr = "0"+str(secs)
        if len(secstr) < 5:
            secstr = secstr + "0"
    else: 
        secstr = str(secs)
        if len(secstr) < 5:
            secstr = secstr + "0"
    if minutes >= 60:
        minutes = minutes % 60
    if minutes < 10:
        minstr ="0"+str(minutes)
    else: 
        minstr = str(minutes)
    if hours <= 0:
        hourstr = ""
    else: hourstr = str(hours) + ":"
    return hourstr+ minstr + ":"+secstr

def format_subtitle_text(subtitle_text, width, max_lines=3):
    """Format subtitle text to fit within terminal width and limit lines"""
    if not subtitle_text:
        return []
    
    # Split by existing newlines first
    lines = subtitle_text.split('\n')
    formatted_lines = []
    
    for line in lines:
        # Word wrap each line to fit terminal width
        words = line.split()
        current_line = ""
        
        for word in words:
            if len(current_line + " " + word) <= width - 4:  # Leave some margin
                if current_line:
                    current_line += " " + word
                else:
                    current_line = word
            else:
                if current_line:
                    formatted_lines.append(current_line)
                current_line = word
        
        if current_line:
            formatted_lines.append(current_line)
    
    # Limit to max_lines
    return formatted_lines[:max_lines]

def play_video(video_path, fps=None, use_color=True, use_blocks=True,srt_path=None,subproc=None):
    """Play video as ASCII art with optional color support"""
    try:
        subtitle_parser = None
        if srt_path != None:
            subtitle_parser = SRTParser(srt_path)
            if subtitle_parser.subtitles:
                print(f"Loaded {len(subtitle_parser.subtitles)} subtitles from {srt_path}")
            else:
                print("No subtitles loaded")
        # Open video file
        cap = cv2.VideoCapture(video_path)
        last_frame_slow = False
        if not cap.isOpened():
            raise Exception("Error: Could not open video file")

        # Get video properties
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        source_fps = cap.get(cv2.CAP_PROP_FPS)
        if fps != None:
            frame_rate = fps
        else:
            frame_rate = cap.get(cv2.CAP_PROP_FPS)



        print(f"Playing video: {os.path.basename(video_path)}")
        print(f"Total frames: {total_frames}")
        print(f"Frame rate: {frame_rate} FPS")

        if use_color:
            print("Color mode: ENABLED")
            if use_blocks:
                print("Using block characters for better color representation")
        else:
            print("Color mode: DISABLED")

        print("Press Ctrl+C to stop playback\n")

        frame_count = 0
        frame_drops = 0
        start_time = time.time()
        # str(1/(abs(time.time() - start_time) - expected_time))
        frametracker = []
        fpsstr="00.00"
        print('\033[?25l', end="")
        while True:
            ret, frame = cap.read()

            if not ret:
                break
            elapsed_playtime = frame_count / source_fps
            
            # Get current subtitle
            current_subtitle = None
            if subtitle_parser:
                current_subtitle = subtitle_parser.get_subtitle_at_time(elapsed_playtime)

            # Resize frame for terminal display
            width,height = get_terminal_dimensions()

            # Reserve space for subtitles if they exist
            subtitle_lines = []
            if current_subtitle:
                subtitle_lines = format_subtitle_text(current_subtitle, width)

            resized_frame = resize_frame(frame, width, height-2)

            # Convert to ASCII art
            if use_color and use_blocks:
                ascii_art = image_to_ascii_blocks(resized_frame, use_color=True)
            else:
                ascii_art = image_to_ascii(resized_frame, use_color=use_color)

            # Clear screen and display ASCII art
            #clear_screen()
            subout=""
            sys.stdout.write('\033[H')
            sys.stdout.write(ascii_art)
            if subtitle_lines:
                lines=0
                for subtitle_line in subtitle_lines:
                    subout+=("\033[43m\033[30m"+subtitle_line+" "+"\033[0m")
                    lines+=1
            midline="\33["+str(height-1)+";"+str(int((width-len(subout))/2))+"H"
            
            frame_count += 1
            
            # Calculate delay for desired FPS
            if frame_rate > 0:
                elapsed_time = time.time() - start_time
                if len(frametracker) < frame_rate: frametracker.append(elapsed_time)
                else: 
                    fps = round(1/(abs(frametracker[0] - frametracker[-1])/(frame_rate-1)),2)
                    if len(str(fps)) == 4:
                        fpsstr=str(fps)+"0"
                    elif len(str(fps)) == 5:
                        fpsstr=str(fps)
                    elif len(str(fps)) == 2:
                        fpsstr=str(fps)+".00"
                    else:
                        fpsstr=str(fps)
                    frametracker = []
                # buffer here and then maybe wait
                etimestr=str(gettimer(elapsed_playtime))
                
                #sleep_time = max(0, elapsed_time - (elapsed_playtime + (1/frame_rate)))
                sleep_time = max (0, (elapsed_playtime - (elapsed_time + (1/frame_rate))))
                time.sleep(sleep_time)

                targetframe = int(elapsed_time/(1/source_fps))
                if targetframe > frame_count:
                    frame_cstatus = "\033[31m"
                else:
                    frame_cstatus = "\033[32m"
                sys.stdout.write("\033["+str(height)+";0H\033[1;30mstats:" + frame_cstatus + str(frame_count)  +"\033[1;30m"+"/" + str(total_frames)+"|drops:"+str(frame_drops) + "|fps tgt/cur: " + str(round(frame_rate,2)) +"/"+fpsstr+ "|"+etimestr+"|wxh:"+str(width)+"x"+str(height)+"|sl:"+str(sleep_time)+"\033[0m")
                sys.stdout.write("\033["+str(height-1)+";0H"+(" "*width))
                sys.stdout.write(midline+subout)
                if elapsed_time - elapsed_playtime > ((1/frame_rate)*.98)*10:
                    #drop next frame -- this method might be causing some slowdown,
                    # reconsider cap.read() and throwing away the frames
                    frame_drops+=targetframe - frame_count
                    cap.set(cv2.CAP_PROP_POS_FRAMES, targetframe)
                    frame_count = targetframe
                elif elapsed_time - elapsed_playtime > ((1/frame_rate)*.98):
                    for i in range(targetframe - frame_count):
                        cap.read()
                        frame_count+=1
                        frame_drops+=1
            
        cap.release()
        print("\nVideo playback completed!")

    except KeyboardInterrupt:
        print("\nPlayback interrupted by user")
        cap.release()
        if subproc != None:
            print("\nKilling VLC pid:" + str(subproc.pid))
            subproc.kill()
    except Exception as e:
        print(f"Error during video playback: {str(e)}")
        if 'cap' in locals():
            cap.release()

def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print("Usage: python aplay.py <video_file> [options]")
        print("Options:")
        print("  --color     Enable color ASCII output")
        #deprecated TODO: remove
        #print("  --blocks    Use block characters (works best with --color)")
        print("  --fps N     Set playback FPS (default: source)")
        print("  --srt (F)   Subtitle support (filename optional)")
        print("  --audio     enable VLC audio playback support")
        print("\nExamples:")
        print("  python aplay.py video.mp4")
        print("  python aplay.py video.mp4 --color")
        print("  python aplay.py video.mp4 --color --fps 30")
        print("  python aplay.py video.mp4 --color --audio --srt")
        print("  python aplay.py video.mp4 --color --audio -srt --fps 30")
        return

    default_vlc_paths=['C:\\Progra~1\\VideoLAN\\VLC\\vlc.exe',"/Applications/VLC.app/Contents/MacOS/VLC","/usr/bin/vlc"]
    for vlc in default_vlc_paths:
        if os.path.exists(vlc):
            vlc_path = vlc
            break
        
    video_path = sys.argv[1]
    use_color = "--color" in sys.argv
    use_blocks = "--blocks" in sys.argv
    vlc_audio = "--audio" in sys.argv
    # Parse SRT argument
    srt_path = None
    if "--srt" in sys.argv:
        try:
            srt_idx = sys.argv.index("--srt")
            if srt_idx + 1 < len(sys.argv):
                srt_path = sys.argv[srt_idx + 1]
        except IndexError:
            print("Error: No SRT file specified after --srt")
            return

    # Parse FPS argument
    fps = None
    if "--fps" in sys.argv:
        try:
            fps_idx = sys.argv.index("--fps")
            if fps_idx + 1 < len(sys.argv):
                fps = int(sys.argv[fps_idx + 1])
        except (ValueError, IndexError):
            print("Invalid FPS value, using default: 15")

    # Check if file exists
    if not os.path.exists(video_path):
        print(f"Error: Video file '{video_path}' not found")
        return

    # Check if it's a valid video file
    valid_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm']
    _, ext = os.path.splitext(video_path)

    if ext.lower() not in valid_extensions:
        print(f"Warning: File extension '{ext}' might not be supported")
        print("Supported formats: mp4, avi, mov, mkv, wmv, flv, webm")

    # Check terminal color support
    if use_color:
        if os.environ.get('TERM', '').find('color') == -1 and os.name != 'nt':
            print("Warning: Your terminal might not support colors properly")
    # Auto-detect SRT file if not specified
    if not srt_path:
        # Try to find SRT file with same name as video
        video_base = os.path.splitext(video_path)[0]
        auto_srt = video_base + '.srt'
        if os.path.exists(auto_srt):
            srt_path = auto_srt
            print(f"Auto-detected SRT file: {auto_srt}")
    
    #prep audio.
    subproc=None
    if vlc_audio:
        subproc=subprocess.Popen([vlc_path, video_path,"--no-video","--play-and-exit","-I dummy",])
    # Play the video
    with keep.presenting():
        # shit starts too quick, TODO: take as arg 
        time.sleep(0.24)
        play_video(video_path, fps=fps, use_color=use_color, use_blocks=use_blocks,srt_path=srt_path,subproc=subproc)
    #processmp.join()

if __name__ == "__main__":
    main()

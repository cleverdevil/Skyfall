# TODO:
# - Leaderboard report for mortals

import asyncio
import pygame
import os
import random
import sys
import re
from datetime import datetime

BROWSER = False

# if running in browser as wasm, fake out the leaderboard
if sys.platform == "emscripten":
    BROWSER = True

    class LeaderboardMock:
        def add_player(self, email, name):
            pass

        def log_session(self, email, session_start, session_end, scores):
            pass

        def get_player_name(self, email):
            return ""

        def get_leaderboard(self, count=10):
            return [
                ("Visit booth #1954 to compete!", None, None),
                ("", None, None),
                ("     Win A PS5 Pro     ", None, None),
                ("", None, None),
                ("", None, None),
                ("", None, None),
                ("See you there!", None, None),
            ]

    leaderboard = LeaderboardMock()
else:
    import leaderboard


# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 1250  # 1250
PLAYER_SIZE = 100
HELICOPTER_SIZE = (100, 50)
INITIAL_OBSTACLE_SPEED = 200
SPEED_INCREMENT = 15
CLOUD_POINT_VALUES = [1, 5, 10]
LIVES = 3
TIME_LIMIT = 300
HEART_PADDING = 20
HUD_PADDING = 10
HUD_BORDER_WIDTH = 5
COMMON_FONT_SIZE = 36
TITLE_BLINK_INTERVAL = 3000
SKYDIVER_MOVE_SPEED = 5
LEADERBOARD_BOX_OPACITY = 40
LEADERBOARD_BOX_WIDTH = SCREEN_WIDTH - 100
LEADERBOARD_BOX_HEIGHT = 400
COLORS = {
    "SKY_BLUE": (135, 206, 235),
    "WHITE": (255, 255, 255),
    "BLACK": (0, 0, 0),
    "GREY": (100, 100, 100),
    "DARK_RED": (139, 0, 0),
    "ORANGE": (255, 165, 0),
    "DARK_BLUE": (0, 0, 139),
    "DARK_GREEN": (0, 100, 0),
}


# Fix joystick initialization failure by monkeypatch
def _fake_init(*a, **k):
    pass


pygame.joystick.init = _fake_init


# load resources from disk
def load_resource(path):
    if BROWSER:
        return path
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    path = os.path.join(base_path, path)
    return path


# Initialize Pygame and fonts
pygame.init()
pygame.font.init()  # Initialize the font module
screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SCALED, vsync=1
)
pygame.display.set_caption("Skyfall")
clock = pygame.time.Clock()

# Load custom fonts from the 'fonts' folder
title_font = pygame.font.Font(load_resource("fonts/title.ttf"), 144)
leaderboard_title_font = pygame.font.Font(
    load_resource("fonts/title.ttf"), 50
)  # 50% size
hud_font = pygame.font.Font(load_resource("fonts/common.otf"), 20)
common_font = pygame.font.Font(load_resource("fonts/common.otf"), COMMON_FONT_SIZE)
small_common_font = pygame.font.Font(
    load_resource("fonts/common.otf"), int(COMMON_FONT_SIZE * 0.75)
)  # Reduced by 25%

# Load images from the 'images' folder
player_image = pygame.image.load(load_resource("images/skydiver.png")).convert_alpha()
mission_image = pygame.image.load(
    load_resource("images/mission.png")
).convert_alpha()  # Logo
dynamic_o_image = pygame.image.load(
    load_resource("images/dynamic-o.png")
).convert_alpha()  # Brand symbol

# Title Screen Animation Variables
title_skydiver_pos = SCREEN_WIDTH // 2
title_skydiver_direction = 1
blink_timer = 0
MAX_SKYDIVER_MOVEMENT = 100


# Utility function to handle text rendering, centered
def render_text_centered(text, font, color, center_x, center_y):
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(center=(center_x, center_y))
    screen.blit(text_surface, text_rect)


# Helper function to display dynamic-o.png in the bottom right corner with padding
def display_brand_symbol():
    dynamic_o_scaled = pygame.transform.scale(
        dynamic_o_image,
        (
            int(dynamic_o_image.get_width() * 0.15),
            int(dynamic_o_image.get_height() * 0.15),
        ),
    )
    symbol_x = SCREEN_WIDTH - dynamic_o_scaled.get_width() - 20
    symbol_y = SCREEN_HEIGHT - dynamic_o_scaled.get_height() - 20
    screen.blit(dynamic_o_scaled, (symbol_x, symbol_y))


# Helper function to validate email format using regex
def is_valid_email(email):
    pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
    return re.match(pattern, email)


# Display leaderboard on the title screen
def display_leaderboard():
    # Fetch top 10 scores from the leaderboard
    top_scores = leaderboard.get_leaderboard(count=8)

    # Create a semi-transparent black box
    leaderboard_box = pygame.Surface((LEADERBOARD_BOX_WIDTH, LEADERBOARD_BOX_HEIGHT))
    leaderboard_box.set_alpha(LEADERBOARD_BOX_OPACITY)
    leaderboard_box.fill(COLORS["BLACK"])
    screen.blit(
        leaderboard_box,
        (
            (SCREEN_WIDTH - LEADERBOARD_BOX_WIDTH) // 2,
            SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 250,
        ),
    )

    # Draw title
    message = "Play at AWS re:Invent to win!" if BROWSER else "High Scores"
    render_text_centered(
        message,
        leaderboard_title_font,
        COLORS["WHITE"],
        SCREEN_WIDTH // 2,
        SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 200,
    )

    # Define leaderboard positions
    leaderboard_start_y = SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 160
    line_height = 35

    for i, (name, score, timestamp) in enumerate(top_scores):
        if not score:
            text = small_common_font.render(name, True, COLORS["WHITE"])
            screen.blit(text, (100, leaderboard_start_y + i * line_height))
            continue

        rank = f"{i + 1}."
        player_name = name if len(name) < 25 else name[:23] + "..."
        score_str = str(int(score))

        # Right-align rank numbers
        rank_text = small_common_font.render(rank, True, COLORS["WHITE"])
        screen.blit(rank_text, (100, leaderboard_start_y + i * line_height))

        # Left-align player names
        name_text = small_common_font.render(player_name, True, COLORS["WHITE"])
        screen.blit(name_text, (160, leaderboard_start_y + i * line_height))

        # Left-align scores
        score_text = small_common_font.render(score_str, True, COLORS["WHITE"])
        screen.blit(score_text, (650, leaderboard_start_y + i * line_height))


# Cloud class for background clouds (no point values)
class BackgroundCloud:
    def __init__(self, cloud_type, speed):
        cloud_images = [
            pygame.image.load("images/cloud1.png").convert_alpha(),
            pygame.image.load("images/cloud2.png").convert_alpha(),
            pygame.image.load("images/cloud3.png").convert_alpha(),
        ]
        self.image = cloud_images[cloud_type]
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = SCREEN_HEIGHT
        self.speed = speed

    def move(self, delta_time):
        self.rect.y -= self.speed * delta_time

    def draw(self):
        screen.blit(self.image, self.rect)


# Title Screen
async def title_screen():
    global title_skydiver_pos, title_skydiver_direction, blink_timer

    # Reset skydiver animation variables on every title screen display
    title_skydiver_pos = SCREEN_WIDTH // 2
    title_skydiver_direction = 1
    blink_timer = 0

    # Create list to hold background clouds
    background_clouds = []

    # Populate initial clouds
    for _ in range(5):  # Start with 5 clouds
        cloud_type = random.randint(0, 2)
        cloud_speed = random.uniform(50, 150)  # Slower clouds
        background_clouds.append(BackgroundCloud(cloud_type, cloud_speed))

    # Scale down the mission.png image by a further 35% (to a total of 45%)
    mission_scaled = pygame.transform.scale(
        mission_image,
        (
            int(mission_image.get_width() * 0.45),
            int(mission_image.get_height() * 0.45),
        ),
    )

    running = True
    while running:
        delta_time = clock.tick(60) / 1000
        screen.fill(COLORS["SKY_BLUE"])

        # Move and draw background clouds
        for cloud in background_clouds[:]:
            cloud.move(delta_time)
            cloud.draw()
            # Remove cloud once it goes off-screen and add a new one
            if cloud.rect.y + cloud.rect.height < 0:
                background_clouds.remove(cloud)
                cloud_type = random.randint(0, 2)
                cloud_speed = random.uniform(50, 150)
                background_clouds.append(BackgroundCloud(cloud_type, cloud_speed))

        # Display title and animate skydiver
        render_text_centered(
            "SKYFALL", title_font, COLORS["WHITE"], SCREEN_WIDTH // 2, 200
        )
        screen.blit(
            player_image, (round(title_skydiver_pos - PLAYER_SIZE // 2), round(350))
        )

        # Animate skydiver position
        title_skydiver_pos += (
            SKYDIVER_MOVE_SPEED * title_skydiver_direction * delta_time
        )
        if title_skydiver_pos < (
            SCREEN_WIDTH // 2 - MAX_SKYDIVER_MOVEMENT
        ) or title_skydiver_pos > (SCREEN_WIDTH // 2 + MAX_SKYDIVER_MOVEMENT):
            title_skydiver_direction *= -1

        blink_timer += delta_time * 1000
        if blink_timer >= TITLE_BLINK_INTERVAL:
            blink_timer = 0
        if blink_timer < TITLE_BLINK_INTERVAL / 2:
            message = "Press ENTER or TOUCH to play"
            render_text_centered(
                message,
                common_font,
                COLORS["DARK_RED"],
                SCREEN_WIDTH // 2,
                550,
            )

        # Show "BROUGHT TO YOU BY" text with reduced font size
        render_text_centered(
            "BROUGHT TO YOU BY",
            small_common_font,  # Smaller font size
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 180,
        )

        # Display scaled mission logo
        screen.blit(
            mission_scaled,
            (
                round((SCREEN_WIDTH - mission_scaled.get_width()) // 2),
                round(SCREEN_HEIGHT - 60 - mission_scaled.get_height()),
            ),
        )

        # Display leaderboard
        display_leaderboard()

        pygame.display.update()
        await asyncio.sleep(0)

        # Handle input events
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                await session_info_screen()
                return
            if BROWSER and event.type == pygame.FINGERUP:
                await session_info_screen()
                return


async def session_info_screen():
    name = ""
    email = ""
    is_typing_name = True
    is_typing_email = False
    error_message = ""
    blink_timer = 0
    cursor_visible = True
    input_box_width = 500  # Increased input box width
    input_box_height = 60  # Increased input box height

    if BROWSER:
        await main_game(name, email)

    # Smaller font for input box text
    input_font = pygame.font.Font("fonts/common.otf", int(COMMON_FONT_SIZE * 0.75))

    # Smaller font for error messages
    error_font = pygame.font.Font("fonts/common.otf", int(COMMON_FONT_SIZE * 0.6))

    while True:
        screen.fill(COLORS["SKY_BLUE"])

        delta_time = clock.tick(60) / 1000  # For the blinking cursor timer
        blink_timer += delta_time * 1000
        if blink_timer >= 500:  # Blink every 500ms
            blink_timer = 0
            cursor_visible = not cursor_visible

        if is_typing_name:
            render_text_centered(
                "Enter your name:",
                common_font,
                COLORS["BLACK"],
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 3,
            )
            input_rect = pygame.Rect(
                round((SCREEN_WIDTH - input_box_width) // 2),
                round(SCREEN_HEIGHT // 3 + 50),
                round(input_box_width),
                round(input_box_height),
            )
            pygame.draw.rect(
                screen, COLORS["BLACK"], input_rect, 1
            )  # 1-pixel black border
            name_text = input_font.render(name, True, COLORS["BLACK"])
            screen.blit(name_text, (round(input_rect.x + 10), round(input_rect.y + 5)))

            if cursor_visible:
                cursor_x = round(input_rect.x + 10 + name_text.get_width() + 2)
                pygame.draw.line(
                    screen,
                    COLORS["BLACK"],
                    (cursor_x, round(input_rect.y + 5)),
                    (cursor_x, round(input_rect.y + 45)),
                    2,
                )

        elif is_typing_email:
            render_text_centered(
                "Enter your email:",
                common_font,
                COLORS["BLACK"],
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 3,
            )
            input_rect = pygame.Rect(
                round((SCREEN_WIDTH - input_box_width) // 2),
                round(SCREEN_HEIGHT // 3 + 50),
                round(input_box_width),
                round(input_box_height),
            )
            pygame.draw.rect(
                screen, COLORS["BLACK"], input_rect, 1
            )  # 1-pixel black border
            email_text = input_font.render(email, True, COLORS["BLACK"])
            screen.blit(
                email_text, (round(input_rect.x + 10), round(input_rect.y + 5))
            )

            if cursor_visible:
                cursor_x = round(input_rect.x + 10 + email_text.get_width() + 2)
                pygame.draw.line(
                    screen,
                    COLORS["BLACK"],
                    (cursor_x, round(input_rect.y + 5)),
                    (cursor_x, round(input_rect.y + 45)),
                    2,
                )

        # Show any error messages
        if error_message:
            lines = error_message.split("\n")  # For multi-line error messages
            for i, line in enumerate(lines):
                render_text_centered(
                    line,
                    error_font,
                    COLORS["DARK_RED"],
                    SCREEN_WIDTH // 2,
                    SCREEN_HEIGHT // 3 + 120 + i * 30,
                )

        pygame.display.update()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    title_screen()
                    return
                if event.key == pygame.K_BACKSPACE:
                    if is_typing_name and len(name) > 0:
                        name = name[:-1]
                    elif is_typing_email and len(email) > 0:
                        email = email[:-1]
                elif event.key == pygame.K_RETURN:
                    if is_typing_name:
                        if len(name) >= 4:
                            is_typing_name = False
                            is_typing_email = True
                        else:
                            error_message = "Name must be at least 4 characters."
                    elif is_typing_email:
                        if is_valid_email(email) and len(email) >= 6:
                            leaderboard.add_player(email, name)
                            await main_game(name, email)
                            return
                        else:
                            error_message = "Please enter a valid email address."
                else:
                    if event.unicode.isprintable():
                        if is_typing_name and len(name) < 30:
                            name += event.unicode
                        if is_typing_email and len(email) < 50:
                            email += event.unicode

            await asyncio.sleep(0)


# Main Game Loop with Lives and Scores
async def main_game(name, email):
    scores = []
    lives = LIVES

    # Check if the player exists, and register them if not
    leaderboard.add_player(email, name)

    # Log the start of a new session
    session_start = datetime.now()

    while lives > 0:
        score, time_survived, cloud_points, max_speed = await play_game(
            lives
        )  # Pass the current number of lives
        await inter_round_screen(score, time_survived, cloud_points, max_speed)
        scores.append(score)
        lives -= 1  # Decrease lives after each game

    # Ensure scores has exactly three elements, filling in with 0 if necessary
    while len(scores) < 3:
        scores.append(0)

    # Log the session at the end, using a list of scores
    session_end = datetime.now()

    leaderboard.log_session(
        email, session_start, session_end, scores
    )  # Pass the scores list

    await end_of_round_screen(scores, email)


# Inter-round screen to display the score after each life
async def inter_round_screen(score, time_survived, cloud_points, max_speed):
    running = True
    while running:
        screen.fill(COLORS["SKY_BLUE"])
        render_text_centered(
            f"Score: {round(score)}",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            200,
        )
        render_text_centered(
            f"Time Alive: {round(time_survived)} seconds",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            300,
        )
        render_text_centered(
            f"Cloud Points: {round(cloud_points)}",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            380,
        )
        render_text_centered(
            f"Max Speed: {round(max_speed)} ft/s",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            460,
        )
        render_text_centered(
            "Press ENTER or TOUCH to continue",
            common_font,
            COLORS["DARK_RED"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 200,
        )

        display_brand_symbol()

        pygame.display.update()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                running = False
            if BROWSER and event.type == pygame.FINGERUP:
                running = False


# End of round screen with leaderboard, blinking session scores, and zooming high score image
async def end_of_round_screen(scores, email):
    running = True
    best_score = max(scores)  # The player's best score in this round
    blink_timer = 0
    blink_on = True  # To control blinking effect
    BLINK_INTERVAL = 500  # 500 ms interval

    # Fetch the top 8 scores including the player's new score
    top_scores = leaderboard.get_leaderboard(count=8)

    # Load the high score image
    highscore_image = pygame.image.load("images/highscore.png").convert_alpha()

    while running:
        delta_time = clock.tick(60) / 1000  # Update the time for blinking effect
        blink_timer += delta_time * 1000
        if blink_timer >= BLINK_INTERVAL:
            blink_timer = 0
            blink_on = not blink_on  # Toggle the blinking state

        screen.fill(COLORS["SKY_BLUE"])

        # Sort and display player's scores
        sorted_scores = sorted(scores, reverse=True)

        # Check if player achieved the top position
        player_is_top = False
        if (
            leaderboard.get_player_name(email) == top_scores[0][0]
            and best_score == top_scores[0][1]
        ):
            player_is_top = True

        # If the player is top, display the highscore.png image
        if player_is_top:
            highscore_rect = highscore_image.get_rect(center=(SCREEN_WIDTH // 2, 200))
            screen.blit(highscore_image, highscore_rect)
        else:
            # Display "End of Round" if player is not the top scorer
            render_text_centered(
                "End of Round", common_font, COLORS["BLACK"], SCREEN_WIDTH // 2, 200
            )

        # Display player's individual scores
        render_text_centered(
            "Your Scores:",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            300,
        )
        for i, score in enumerate(sorted_scores):
            render_text_centered(
                f"Score {i + 1}: {round(score)}",
                common_font,
                COLORS["BLACK"],
                SCREEN_WIDTH // 2,
                360 + i * 60,
            )

        # Create a semi-transparent black box for the leaderboard
        leaderboard_box = pygame.Surface(
            (LEADERBOARD_BOX_WIDTH, LEADERBOARD_BOX_HEIGHT)
        )
        leaderboard_box.set_alpha(LEADERBOARD_BOX_OPACITY)
        leaderboard_box.fill(COLORS["BLACK"])
        screen.blit(
            leaderboard_box,
            (
                (SCREEN_WIDTH - LEADERBOARD_BOX_WIDTH) // 2,
                SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 250,
            ),
        )

        # Draw title
        message = "Play at AWS re:Invent to win!" if BROWSER else "High Scores"
        render_text_centered(
            message,
            leaderboard_title_font,
            COLORS["WHITE"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 200,
        )

        # Define leaderboard positions
        leaderboard_start_y = SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 160
        line_height = 35

        # Display top scores, highlighting session scores in red with blinking effect
        for i, (name, score, timestamp) in enumerate(top_scores):
            if not score:
                text = small_common_font.render(name, True, COLORS["WHITE"])
                screen.blit(text, (100, leaderboard_start_y + i * line_height))
                continue

            rank = f"{i + 1}."
            player_name = name if len(name) < 25 else name[:23] + "..."
            score_str = str(int(score)) if score else ""

            # Determine if this score is part of the current session
            is_current_session = (name == leaderboard.get_player_name(email)) and (
                score in scores
            )

            # Set the color and blinking for current session scores
            if is_current_session and blink_on:
                color = COLORS["DARK_RED"]  # Blink the current session scores in red
            else:
                color = COLORS["WHITE"]  # Normal scores are in white

            # Right-align rank numbers
            rank_text = small_common_font.render(rank, True, color)
            screen.blit(rank_text, (100, leaderboard_start_y + i * line_height))

            # Left-align player names
            name_text = small_common_font.render(player_name, True, color)
            screen.blit(name_text, (160, leaderboard_start_y + i * line_height))

            # Left-align scores
            score_text = small_common_font.render(score_str, True, color)
            screen.blit(score_text, (650, leaderboard_start_y + i * line_height))

        # Indicate the player's best score and ranking
        player_rank = None
        for i, (name, score, timestamp) in enumerate(top_scores):
            if name == leaderboard.get_player_name(email) and score == best_score:
                player_rank = i + 1
                break

        if player_rank and not player_is_top:
            render_text_centered(
                f"You are ranked {player_rank} with a score of {int(best_score)}",
                small_common_font,
                COLORS["DARK_RED"],
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT - 120,
            )

        render_text_centered(
            "Press ENTER or TOUCH to restart",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 120,
        )

        display_brand_symbol()

        pygame.display.update()
        await asyncio.sleep(0)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                await title_screen()
                return
            if BROWSER and event.type == pygame.FINGERUP:
                await title_screen()
                return


# Game Logic for each life
async def play_game(lives):
    player = Player()
    obstacles = []
    helicopters = []
    total_cloud_points = 0
    time_survived = 0
    obstacle_speed = INITIAL_OBSTACLE_SPEED
    running = True
    max_speed = obstacle_speed
    start_time = pygame.time.get_ticks()

    # Flags for tracking continuous touch steering
    steer_left = False
    steer_right = False

    while running:
        delta_time = clock.tick(60) / 1000
        time_survived = (pygame.time.get_ticks() - start_time) / 1000
        obstacle_speed += SPEED_INCREMENT * delta_time  # Increment speed gradually
        max_speed = max(max_speed, obstacle_speed)

        if time_survived > TIME_LIMIT:
            score = (10 * time_survived) + total_cloud_points
            return score, time_survived, total_cloud_points, max_speed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            # Handle keyboard controls
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    steer_left = True
                elif event.key == pygame.K_RIGHT:
                    steer_right = True
            elif event.type == pygame.KEYUP:
                if event.key == pygame.K_LEFT:
                    steer_left = False
                elif event.key == pygame.K_RIGHT:
                    steer_right = False

            # Handle touch controls
            elif event.type == pygame.FINGERDOWN:
                # Check if the touch is on the left or right side of the screen
                if event.x < 0.5:
                    steer_left = True
                    steer_right = False  # Prevent dual direction steering
                else:
                    steer_right = True
                    steer_left = False  # Prevent dual direction steering
            elif event.type == pygame.FINGERUP:
                # Release steering when finger is lifted
                steer_left = False
                steer_right = False

        # Move player based on steering flags
        if steer_left:
            player.handle_movement({pygame.K_LEFT: True})
        elif steer_right:
            player.handle_movement({pygame.K_RIGHT: True})
        else:
            player.handle_movement({})  # No movement when no touch or key press

        # Spawn clouds and helicopters
        if random.random() < 0.02:
            cloud_type = random.randint(0, 2)
            obstacles.append(Cloud(cloud_type, obstacle_speed))
        if random.random() < 0.01:
            helicopters.append(Helicopter(obstacle_speed))

        # Move and check collisions for obstacles
        for obstacle in obstacles[:]:
            obstacle.move(delta_time)
            if isinstance(obstacle, Cloud) and player.rect.colliderect(obstacle.rect):
                total_cloud_points += obstacle.point_value
                obstacles.remove(obstacle)

        # Handle helicopter collisions
        for helicopter in helicopters[:]:
            helicopter.move(delta_time)
            if player.rect.colliderect(helicopter.rect) and not helicopter.exploded:
                score = (10 * time_survived) + total_cloud_points
                return score, time_survived, total_cloud_points, max_speed

        handle_helicopter_collisions(helicopters)

        # Redraw screen
        screen.fill(COLORS["SKY_BLUE"])
        player.draw()
        for obstacle in obstacles:
            obstacle.draw()
        for helicopter in helicopters:
            helicopter.draw()

        # Update the HUD and display lives
        draw_hud(time_survived, total_cloud_points, obstacle_speed)
        display_lives(lives)

        # Show brand symbol (dynamic-o.png) in the bottom right
        display_brand_symbol()

        pygame.display.update()
        await asyncio.sleep(0)

    return (
        round((10 * time_survived) + total_cloud_points),
        round(time_survived),
        round(total_cloud_points),
        round(max_speed),
    )


# Handle helicopter collisions
def handle_helicopter_collisions(helicopters):
    for helicopter in helicopters:
        if helicopter.exploded:
            continue
        for other_heli in helicopters:
            if (
                other_heli != helicopter
                and other_heli.rect.colliderect(helicopter.rect)
                and not other_heli.exploded
            ):
                helicopter.exploded = True
                other_heli.exploded = True


# Draw HUD
def draw_hud(time_survived, cloud_points, speed):
    hud_width = 250
    hud_height = 110

    time_text = hud_font.render(f"Time: {int(time_survived)} s", True, COLORS["WHITE"])
    cloud_text = hud_font.render(
        f"Cloud Points: {cloud_points}", True, COLORS["WHITE"]
    )
    speed_text = hud_font.render(f"Speed: {int(speed)} ft/s", True, COLORS["WHITE"])
    hud_surface = pygame.Surface((hud_width, hud_height))
    hud_surface.set_alpha(100)
    hud_surface.fill(COLORS["BLACK"])
    screen.blit(hud_surface, (10, 10))

    pygame.draw.rect(screen, COLORS["BLACK"], (10, 10, hud_width, hud_height), 1)

    screen.blit(time_text, (20, 20))
    screen.blit(cloud_text, (20, 20 + time_text.get_height() + 4))
    screen.blit(speed_text, (20, 20 + 2 * (time_text.get_height() + 4)))


# Player class
class Player:
    def __init__(self):
        self.image = pygame.transform.scale(
            player_image, (100, 91)
        )  # Base image without rotation
        self.rect = self.image.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT // 3))
        self.rotation_angle = 0  # Angle for tilting the image

    def move(self, dx):
        self.rect.x += dx
        self.rect.x = max(0, min(SCREEN_WIDTH - self.rect.width, self.rect.x))

        # Update the rotation angle based on movement direction
        if dx > 0:  # Moving right
            if self.rotation_angle >= -15:
                self.rotation_angle -= 1  # Tilt to the left (negative angle)
        elif dx < 0:  # Moving left
            if self.rotation_angle <= 15:
                self.rotation_angle += 1
        else:
            if self.rotation_angle > 0:
                self.rotation_angle -= 1
            elif self.rotation_angle < 0:
                self.rotation_angle += 1
            self.rotation_angle = 0

    def handle_movement(self, keys):
        if keys.get(pygame.K_LEFT):
            self.move(-5)
        elif keys.get(pygame.K_RIGHT):
            self.move(5)
        else:
            self.move(0)  # No movement, keep the position and reset tilt

    def draw(self):
        # Rotate the image based on the current rotation angle
        rotated_image = pygame.transform.rotate(self.image, self.rotation_angle)
        rotated_rect = rotated_image.get_rect(center=self.rect.center)
        screen.blit(rotated_image, rotated_rect)


# Cloud class
class Cloud:
    def __init__(self, cloud_type, speed):
        cloud_images = [
            pygame.image.load("images/cloud1.png").convert_alpha(),
            pygame.image.load("images/cloud2.png").convert_alpha(),
            pygame.image.load("images/cloud3.png").convert_alpha(),
        ]
        self.image = cloud_images[cloud_type]
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = SCREEN_HEIGHT
        self.speed = speed
        self.point_value = CLOUD_POINT_VALUES[cloud_type]

        # Set the text color based on point value
        self.text_color = {
            1: COLORS["DARK_BLUE"],
            5: COLORS["DARK_GREEN"],
            10: COLORS["DARK_RED"],
        }[self.point_value]

    def move(self, delta_time):
        self.rect.y -= self.speed * delta_time

    def draw(self):
        screen.blit(self.image, self.rect)
        # Draw the point value on top of the cloud using "fonts/common.otf" font
        font_size = self.rect.height  # Set font size proportional to cloud height
        font = pygame.font.Font("fonts/common.otf", font_size)
        point_text = font.render(str(self.point_value), True, self.text_color)
        point_rect = point_text.get_rect(center=self.rect.center)
        screen.blit(point_text, point_rect)


# Helicopter class
class Helicopter:
    def __init__(self, speed):
        self.image = pygame.transform.scale(
            pygame.image.load("images/helicopter.png").convert_alpha(), HELICOPTER_SIZE
        )
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, SCREEN_WIDTH - self.rect.width)
        self.rect.y = SCREEN_HEIGHT
        self.speed = speed
        self.horizontal_speed = random.uniform(40, 120)
        self.direction = random.choice([-1, 1])
        self.exploded = False
        self.opacity = 255

    def move(self, delta_time):
        if not self.exploded:
            self.rect.y -= self.speed * delta_time
            self.rect.x += self.horizontal_speed * delta_time * self.direction
            if self.rect.left <= 0 or self.rect.right >= SCREEN_WIDTH:
                self.direction *= -1
        else:
            self.rect.y -= 200 * delta_time
            self.opacity = max(0, self.opacity - 51 * delta_time)

    def draw(self):
        if self.exploded:
            explosion_surface = pygame.image.load(
                "images/explosion.png"
            ).convert_alpha()
            explosion_surface.set_alpha(int(self.opacity))
            screen.blit(explosion_surface, self.rect)
        else:
            image_to_draw = (
                self.image
                if self.direction == -1
                else pygame.transform.flip(self.image, True, False)
            )
            screen.blit(image_to_draw, self.rect)


# Function to display hearts representing remaining lives
def display_lives(lives):
    heart_full_image = pygame.transform.scale(
        pygame.image.load("images/heart-full.png").convert_alpha(), (50, 50)
    )
    heart_empty_image = pygame.transform.scale(
        pygame.image.load("images/heart-empty.png").convert_alpha(), (50, 50)
    )
    for i in range(LIVES):
        heart_x = SCREEN_WIDTH - HEART_PADDING - (i * 60) - 50
        heart_image = (
            heart_full_image if i < lives else heart_empty_image
        )  # Show full heart if i < lives, otherwise empty heart
        screen.blit(heart_image, (heart_x, 10))


if __name__ == "__main__":
    asyncio.run(title_screen())

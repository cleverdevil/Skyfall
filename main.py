import os
import re
import sys
import random
import asyncio

from datetime import datetime

import pygame

BROWSER = False

# If running in browser as wasm, fake out the leaderboard
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
SCREEN_HEIGHT = 1250
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


# Fix joystick initialization failure by monkeypatching pygame. I feel dirty.
def _fake_init(*a, **k):
    pass


pygame.joystick.init = _fake_init


# Load resources from disk in a way compatible with PyInstaller and Pygbag
def resource(path):
    if BROWSER:
        return path
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    path = os.path.join(base_path, path)
    return path


# Initialize pygame
pygame.init()
pygame.font.init()
screen = pygame.display.set_mode(
    (SCREEN_WIDTH, SCREEN_HEIGHT), flags=pygame.SCALED, vsync=1
)
pygame.display.set_caption("Skyfall")
clock = pygame.time.Clock()

# Load custom fonts
title_font = pygame.font.Font(resource("fonts/title.ttf"), 144)
leaderboard_title_font = pygame.font.Font(resource("fonts/title.ttf"), 50)
hud_font = pygame.font.Font(resource("fonts/common.otf"), 20)
common_font = pygame.font.Font(resource("fonts/common.otf"), COMMON_FONT_SIZE)
small_common_font = pygame.font.Font(
    resource("fonts/common.otf"), int(COMMON_FONT_SIZE * 0.75)
)

# Load images
player_image = pygame.image.load(resource("images/skydiver.png")).convert_alpha()
mission_image = pygame.image.load(resource("images/mission.png")).convert_alpha()
dynamic_o_image = pygame.image.load(resource("images/dynamic-o.png")).convert_alpha()


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


# Cloud class for background clouds displayed on title screen
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


class View:

    def __init__(self):
        self.screen = screen

    async def render_text(self, text, font, color, center_x, center_y):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(center_x, center_y))
        self.screen.blit(text_surface, text_rect)

    async def draw(self):
        raise NotImplementedError()

    async def handle_event(self, event):
        raise NotImplementedError()

    async def stop(self):
        self.running = False

    async def run(self):
        self.running = True
        while self.running:
            # Draw the screen
            await self.draw()

            pygame.display.update()
            await asyncio.sleep(0)

            # handle events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                await self.handle_event(event)
                pygame.display.update()
                clock.tick()
                await asyncio.sleep(0)

        return self


class TitleView(View):

    def __init__(self):
        super().__init__()

        self._max_skydiver_movement = 100
        self._skydiver_pos = SCREEN_WIDTH // 2
        self._skydiver_direction = 1
        self._blink_timer = 0
        self._delta_time = clock.tick(60) / 1000
        self._populate_clouds()

    async def handle_event(self, event):
        # If the user presses 'Return', go to session info screen
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await SessionInfoView().run()

        # If the user is on mobile and taps the screen, go to session into screen
        elif BROWSER and event.type == pygame.FINGERUP:
            await SessionInfoView().run()
            return

    async def draw(self):
        self.screen.fill(COLORS["SKY_BLUE"])

        # Draw clouds
        await self._draw_clouds()

        # Draw leaderboard
        await self._draw_leaderboard()

        # Draw title
        await self.render_text(
            "SKYFALL", title_font, COLORS["WHITE"], SCREEN_WIDTH // 2, 200
        )

        # Draw skydiver
        await self._draw_skydiver()

        # Draw message
        await self._draw_message()

        # Display a branded message about Mission, including our logo
        self._mission_scaled = pygame.transform.scale(
            mission_image,
            (
                int(mission_image.get_width() * 0.45),
                int(mission_image.get_height() * 0.45),
            ),
        )

        await self.render_text(
            "BROUGHT TO YOU BY",
            small_common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 180,
        )
        self.screen.blit(
            self._mission_scaled,
            (
                round((SCREEN_WIDTH - self._mission_scaled.get_width()) // 2),
                round(SCREEN_HEIGHT - 60 - self._mission_scaled.get_height()),
            ),
        )

    async def _draw_skydiver(self):
        # Draw the skydiver
        self.screen.blit(
            player_image,
            (round(self._skydiver_pos - PLAYER_SIZE // 2), round(350)),
        )

        # Animate skydiver position
        self._skydiver_pos += (
            SKYDIVER_MOVE_SPEED * self._skydiver_direction * self._delta_time
        )
        if self._skydiver_pos < (
            SCREEN_WIDTH // 2 - self._max_skydiver_movement
        ) or self._skydiver_pos > (SCREEN_WIDTH // 2 + self._max_skydiver_movement):
            self._skydiver_direction *= -1

    async def _draw_message(self):
        # Display blinking text that tells the player how to start the game
        self._blink_timer += self._delta_time * 1000
        if self._blink_timer >= TITLE_BLINK_INTERVAL:
            self._blink_timer = 0

        if self._blink_timer < TITLE_BLINK_INTERVAL / 2:
            message = "Press ENTER or TOUCH to play"
            await self.render_text(
                message,
                common_font,
                COLORS["DARK_RED"],
                SCREEN_WIDTH // 2,
                550,
            )

    def _populate_clouds(self):
        # Create list to hold background clouds
        self._background_clouds = []

        # Populate five clouds of random types moving at random speeds
        for _ in range(5):
            cloud_type = random.randint(0, 2)
            cloud_speed = random.uniform(50, 150)
            self._background_clouds.append(BackgroundCloud(cloud_type, cloud_speed))

    async def _draw_clouds(self):
        # Move and draw background clouds
        for cloud in self._background_clouds[:]:
            cloud.move(self._delta_time)
            cloud.draw()

            # Remove cloud once it goes off-screen and add a new one
            if cloud.rect.y + cloud.rect.height < 0:
                self._background_clouds.remove(cloud)
                cloud_type = random.randint(0, 2)
                cloud_speed = random.uniform(50, 150)
                self._background_clouds.append(
                    BackgroundCloud(cloud_type, cloud_speed)
                )

    async def _draw_leaderboard(self):
        # Fetch top 10 scores from the leaderboard
        top_scores = leaderboard.get_leaderboard(count=8)

        # Create a semi-transparent black box
        leaderboard_box = pygame.Surface(
            (LEADERBOARD_BOX_WIDTH, LEADERBOARD_BOX_HEIGHT)
        )
        leaderboard_box.set_alpha(LEADERBOARD_BOX_OPACITY)
        leaderboard_box.fill(COLORS["BLACK"])
        self.screen.blit(
            leaderboard_box,
            (
                (SCREEN_WIDTH - LEADERBOARD_BOX_WIDTH) // 2,
                SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 250,
            ),
        )

        # Draw title
        message = "Play at AWS re:Invent to win!" if BROWSER else "High Scores"
        await self.render_text(
            message,
            leaderboard_title_font,
            COLORS["WHITE"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 200,
        )

        # Define leaderboard positions
        leaderboard_start_y = SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 160
        line_height = 35

        # Draw the leaderboard itself
        for i, (name, score, _) in enumerate(top_scores):
            if not score:
                text = small_common_font.render(name, True, COLORS["WHITE"])
                self.screen.blit(text, (100, leaderboard_start_y + i * line_height))
                continue

            rank = f"{i + 1}."
            player_name = name if len(name) < 25 else name[:23] + "..."
            score_str = str(int(score))

            # Right-align rank numbers
            rank_text = small_common_font.render(rank, True, COLORS["WHITE"])
            self.screen.blit(rank_text, (100, leaderboard_start_y + i * line_height))

            # Left-align player names
            name_text = small_common_font.render(player_name, True, COLORS["WHITE"])
            self.screen.blit(name_text, (160, leaderboard_start_y + i * line_height))

            # Left-align scores
            score_text = small_common_font.render(score_str, True, COLORS["WHITE"])
            self.screen.blit(score_text, (650, leaderboard_start_y + i * line_height))


class SessionInfoView(View):

    def __init__(self):
        super().__init__()
        self._name = ""
        self._email = ""
        self._is_typing_name = True
        self._is_typing_email = False
        self._error_message = ""
        self._blink_timer = 0
        self._cursor_visible = True
        self._input_box_width = 500
        self._input_box_height = 60
        self._load_fonts()

    async def _set_cursor_timing(self):
        self._delta_time = clock.tick(60) / 1000
        self._blink_timer += self._delta_time * 1000
        if self._blink_timer >= 500:
            self._blink_timer = 0
            self._cursor_visible = not self._cursor_visible

    async def _draw_input(self, message, target):
        await self.render_text(
            message,
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT // 3,
        )

        input_rect = pygame.Rect(
            round((SCREEN_WIDTH - self._input_box_width) // 2),
            round(SCREEN_HEIGHT // 3 + 50),
            round(self._input_box_width),
            round(self._input_box_height),
        )
        pygame.draw.rect(self.screen, COLORS["BLACK"], input_rect, 1)

        text = self._input_font.render(target, True, COLORS["BLACK"])
        self.screen.blit(text, (round(input_rect.x + 10), round(input_rect.y + 5)))

        if self._cursor_visible:
            cursor_x = round(input_rect.x + 10 + text.get_width() + 2)
            pygame.draw.line(
                self.screen,
                COLORS["BLACK"],
                (cursor_x, round(input_rect.y + 5)),
                (cursor_x, round(input_rect.y + 45)),
                2,
            )

    async def _draw_name_input(self):
        await self._draw_input("Enter your name:", self._name)

    async def _draw_email_input(self):
        await self._draw_input("Enter your email:", self._email)

    async def _handle_validation_errors(self):
        lines = self._error_message.split("\n")
        for i, line in enumerate(lines):
            await self.render_text(
                line,
                self._error_font,
                COLORS["DARK_RED"],
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT // 3 + 120 + i * 30,
            )

    async def draw(self):
        # Don't bother collecting information if running in the browser
        if BROWSER:
            await main_game()
            return

        self.screen.fill(COLORS["SKY_BLUE"])

        # Prepare to display a blinking cursor in input fields
        await self._set_cursor_timing()

        # Display an editable text field for the player name
        if self._is_typing_name:
            await self._draw_name_input()

        # Display an editable text field for the player email address
        elif self._is_typing_email:
            await self._draw_email_input()

        # If validation fails, gracefully tell the user why
        if self._error_message:
            await self._handle_validation_errors()

    async def handle_event(self, event):
        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            await TitleView().run()
            return
        if event.key == pygame.K_BACKSPACE:
            if self._is_typing_name and len(self._name) > 0:
                self._name = self._name[:-1]
            elif self._is_typing_email and len(self._email) > 0:
                self._email = self._email[:-1]
        elif event.key == pygame.K_RETURN:
            if self._is_typing_name:
                if len(self._name) >= 4:
                    self._is_typing_name = False
                    self._is_typing_email = True
                else:
                    self._error_message = "Name must be at least 4 characters."
            elif self._is_typing_email:
                if self._is_valid_email(self._email) and len(self._email) >= 6:
                    leaderboard.add_player(self._email, self._name)
                    await main_game(self._name, self._email)
                    return
                else:
                    self._error_message = "Please enter a valid email address."
        else:
            if event.unicode.isprintable():
                if self._is_typing_name and len(self._name) < 30:
                    self._name += event.unicode
                if self._is_typing_email and len(self._email) < 50:
                    self._email += event.unicode

    def _load_fonts(self):
        self._input_font = pygame.font.Font(
            resource("fonts/common.otf"), int(COMMON_FONT_SIZE * 0.75)
        )
        self._error_font = pygame.font.Font(
            resource("fonts/common.otf"), int(COMMON_FONT_SIZE * 0.6)
        )

    def _is_valid_email(self, email):
        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(pattern, email)


# Main game loop
async def main_game(name="", email=""):
    scores = []
    lives = LIVES

    # Check if the player exists, and register them if not
    leaderboard.add_player(email, name)

    # Log the start of a new session
    session_start = datetime.now()

    # Give the user three "lives", recording the scores for later, and displaying an
    # inter-round screen to summarize the "life"
    while lives > 0:
        # score, time_survived, cloud_points, max_speed = await play_game(lives)
        session = await GameView(lives).run()
        score, time_survived, cloud_points, max_speed = await session.get_results()

        await InterRoundView(score, time_survived, cloud_points, max_speed).run()
        scores.append(score)
        lives -= 1

    # Log the session at the end
    session_end = datetime.now()
    leaderboard.log_session(email, session_start, session_end, scores)

    # Display an end of game screen before returning to the title screen
    await EndOfRoundView(scores, name, email).run()


class InterRoundView(View):

    def __init__(self, score, time_survived, cloud_points, max_speed):
        super().__init__()
        self._score = score
        self._time_survived = time_survived
        self._cloud_points = cloud_points
        self._max_speed = max_speed

    async def draw(self):
        self.screen.fill(COLORS["SKY_BLUE"])
        await self.render_text(
            f"Score: {round(self._score)}",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            200,
        )
        await self.render_text(
            f"Time Alive: {round(self._time_survived)} seconds",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            300,
        )
        await self.render_text(
            f"Cloud Points: {round(self._cloud_points)}",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            380,
        )
        await self.render_text(
            f"Max Speed: {round(self._max_speed)} ft/s",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            460,
        )
        await self.render_text(
            "Press ENTER or TOUCH to continue",
            common_font,
            COLORS["DARK_RED"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 200,
        )

        display_brand_symbol()

    async def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await self.stop()
        if BROWSER and event.type == pygame.FINGERUP:
            await self.stop()


class EndOfRoundView(View):

    def __init__(self, scores, name, email):
        super().__init__()
        self._scores = sorted(scores, reverse=True)
        self._name = name
        self._email = email
        self._best_score = max(scores)
        self._blink_timer = 0
        self._blink_on = True
        self._blink_interval = 500
        self._fetch_leaderboard()

        # Load the high score image
        self._highscore_image = pygame.image.load(
            "images/highscore.png"
        ).convert_alpha()

    def _fetch_leaderboard(self):
        # Fetch the top 8 scores including the player's latest scores
        self._top_scores = leaderboard.get_leaderboard(count=8)

        # Check if player achieved the top position
        self._player_is_top = leaderboard.is_high_score(self._best_score)

    async def _update_blink(self):
        self._delta_time = clock.tick(60) / 1000
        self._blink_timer += self._delta_time * 1000
        if self._blink_timer >= self._blink_interval:
            self._blink_timer = 0
            self._blink_on = not self._blink_on

    async def _draw_header(self):
        # If the player is top, display the highscore.png image
        if self._player_is_top:
            highscore_rect = self._highscore_image.get_rect(
                center=(SCREEN_WIDTH // 2, 200)
            )
            self.screen.blit(self._highscore_image, highscore_rect)

        # Display "End of Round" if player is not the top scorer
        else:
            await self.render_text(
                "End of Round", common_font, COLORS["BLACK"], SCREEN_WIDTH // 2, 200
            )

    async def _draw_player_scores(self):
        await self.render_text(
            "Your Scores:",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            300,
        )
        for i, score in enumerate(self._scores):
            await self.render_text(
                f"Score {i + 1}: {round(score)}",
                common_font,
                COLORS["BLACK"],
                SCREEN_WIDTH // 2,
                360 + i * 60,
            )

    async def draw(self):
        # Draw background
        self.screen.fill(COLORS["SKY_BLUE"])

        # Track blink timing
        await self._update_blink()

        # Draw header based upon top score
        await self._draw_header()

        # Draw player's individual scores for this session of play
        await self._draw_player_scores()

        # Draw the leaderboard, highlighting the players scores
        await self._draw_leaderboard()

        # Draw a summary of player's scores in this session
        await self._draw_summary()

        # Draw instructions for proceeding to the title screen
        await self._draw_instructions()

    async def _draw_leaderboard(self):
        # Create a semi-transparent black box for the leaderboard
        leaderboard_box = pygame.Surface(
            (LEADERBOARD_BOX_WIDTH, LEADERBOARD_BOX_HEIGHT)
        )
        leaderboard_box.set_alpha(LEADERBOARD_BOX_OPACITY)
        leaderboard_box.fill(COLORS["BLACK"])
        self.screen.blit(
            leaderboard_box,
            (
                (SCREEN_WIDTH - LEADERBOARD_BOX_WIDTH) // 2,
                SCREEN_HEIGHT - LEADERBOARD_BOX_HEIGHT - 250,
            ),
        )

        # Draw title
        message = "Play at AWS re:Invent to win!" if BROWSER else "High Scores"
        await self.render_text(
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
        for i, (name, score, _) in enumerate(self._top_scores):
            if not score:
                text = small_common_font.render(name, True, COLORS["WHITE"])
                self.screen.blit(text, (100, leaderboard_start_y + i * line_height))
                continue

            rank = f"{i + 1}."
            player_name = name if len(name) < 25 else name[:23] + "..."
            score_str = str(int(score)) if score else ""

            # Determine if this score is part of the current session
            is_current_session = (name == self._name) and (score in self._scores)

            # Set the color and blinking for current session scores
            if is_current_session and self._blink_on:
                color = COLORS["DARK_RED"]  # Blink the current session scores in red
            else:
                color = COLORS["WHITE"]  # Normal scores are in white

            # Right-align rank numbers
            rank_text = small_common_font.render(rank, True, color)
            self.screen.blit(rank_text, (100, leaderboard_start_y + i * line_height))

            # Left-align player names
            name_text = small_common_font.render(player_name, True, color)
            self.screen.blit(name_text, (160, leaderboard_start_y + i * line_height))

            # Left-align scores
            score_text = small_common_font.render(score_str, True, color)
            self.screen.blit(score_text, (650, leaderboard_start_y + i * line_height))

    async def _draw_summary(self):
        # Indicate the player's best score and ranking
        player_rank = None
        for i, (name, score, _) in enumerate(self._top_scores):
            if (name == self._name) and (score == self._best_score):
                player_rank = i + 1
                break

        if player_rank and not self._player_is_top:
            await self.render_text(
                f"You are ranked {player_rank} with a score of {int(self._best_score)}",
                small_common_font,
                COLORS["DARK_RED"],
                SCREEN_WIDTH // 2,
                SCREEN_HEIGHT - 120,
            )

    async def _draw_instructions(self):
        await self.render_text(
            "Press ENTER or TOUCH to restart",
            common_font,
            COLORS["BLACK"],
            SCREEN_WIDTH // 2,
            SCREEN_HEIGHT - 120,
        )

        # TODO: Move this to the View class
        display_brand_symbol()

    async def handle_event(self, event):
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await TitleView().run()
            return
        if BROWSER and event.type == pygame.FINGERUP:
            await TitleView().run()
            return


class GameView(View):

    def __init__(self, lives):
        super().__init__()
        self._lives = lives
        self._player = Player()
        self._clouds = []
        self._helicopters = []
        self._total_cloud_points = 0
        self._time_survived = 0
        self._obstacle_speed = INITIAL_OBSTACLE_SPEED
        self._max_speed = INITIAL_OBSTACLE_SPEED
        self._start_time = pygame.time.get_ticks()
        self._delta_time = clock.tick(60) / 1000

        # Flags for tracking continuous touch steering
        self._steer_left = False
        self._steer_right = False

    async def draw(self):
        self._delta_time = clock.tick(60) / 1000
        self._time_survived = (pygame.time.get_ticks() - self._start_time) / 1000
        self._obstacle_speed += (
            SPEED_INCREMENT * self._delta_time
        )  # Increment speed gradually
        self._max_speed = max(self._max_speed, self._obstacle_speed)

        if self._time_survived > TIME_LIMIT:
            self._score = (10 * self._time_survived) + self._total_cloud_points
            return

        # Move player based on steering flags
        if self._steer_left:
            self._player.handle_movement({pygame.K_LEFT: True})
        elif self._steer_right:
            self._player.handle_movement({pygame.K_RIGHT: True})
        else:
            self._player.handle_movement({})  # No movement when no touch or key press

        # Spawn clouds and helicopters
        if random.random() < 0.02:
            cloud_type = random.randint(0, 2)
            self._clouds.append(Cloud(cloud_type, self._obstacle_speed))
        if random.random() < 0.01:
            self._helicopters.append(Helicopter(self._obstacle_speed))

        # Move and check collisions for clouds
        for cloud in self._clouds[:]:
            cloud.move(self._delta_time)
            if self._player.rect.colliderect(cloud.rect):
                self._total_cloud_points += cloud.point_value
                self._clouds.remove(cloud)

        # Handle helicopter collisions
        for helicopter in self._helicopters[:]:
            helicopter.move(self._delta_time)
            if (
                self._player.rect.colliderect(helicopter.rect)
                and not helicopter.exploded
            ):
                self._score = (10 * self._time_survived) + self._total_cloud_points
                await self.stop()
                return

        handle_helicopter_collisions(self._helicopters)

        # Redraw screen
        self.screen.fill(COLORS["SKY_BLUE"])
        self._player.draw()
        for cloud in self._clouds:
            cloud.draw()
        for helicopter in self._helicopters:
            helicopter.draw()

        # Update the HUD and display lives
        draw_hud(self._time_survived, self._total_cloud_points, self._obstacle_speed)
        display_lives(self._lives)

        # Show brand symbol (dynamic-o.png) in the bottom right
        display_brand_symbol()

    async def handle_event(self, event):
        # Handle keyboard controls
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_LEFT:
                self._steer_left = True
            elif event.key == pygame.K_RIGHT:
                self._steer_right = True
        elif event.type == pygame.KEYUP:
            if event.key == pygame.K_LEFT:
                self._steer_left = False
            elif event.key == pygame.K_RIGHT:
                self._steer_right = False

        # Handle touch controls
        elif event.type == pygame.FINGERDOWN:
            # Check if the touch is on the left or right side of the screen
            if event.x < 0.5:
                self._steer_left = True
                self._steer_right = False  # Prevent dual direction steering
            else:
                self._steer_right = True
                self._steer_left = False  # Prevent dual direction steering
        elif event.type == pygame.FINGERUP:
            # Release steering when finger is lifted
            self._steer_left = False
            self._steer_right = False

    async def get_results(self):
        return (
            round((10 * self._time_survived) + self._total_cloud_points),
            round(self._time_survived),
            round(self._total_cloud_points),
            round(self._max_speed),
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
        font = pygame.font.Font(resource("fonts/common.otf"), font_size)
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
    asyncio.run(TitleView().run())

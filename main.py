import os
import re
import sys
import random
import asyncio

from datetime import datetime

import pygame

# Enable VSync for SDL renderer
os.environ["SDL_RENDER_VSYNC"] = "1"

# If running in browser as wasm, fake out the leaderboard
BROWSER = True if sys.platform == "emscripten" else False
if not BROWSER:
    import leaderboard
else:
    import platform

    platform.window.canvas.style.imageRendering = "pixelated"


def resource(path):
    """
    Loads images and fonts from disk using a technique compatible with running the
    game locally, on the web, or as an app.
    """

    if BROWSER:
        return path
    base_path = getattr(sys, "_MEIPASS", os.path.abspath("."))
    path = os.path.join(base_path, path)
    return path


class SkyfallGame:
    """
    Main game, which is responsible for initializing pygame, owning the shared clock,
    loading fonts and images, and providing an aggregation point for all "views" within
    the game.
    """

    # Constants
    screen_width = 800
    screen_height = 1250
    scaled_width = 800
    scaled_height = 1250
    total_lives = 3
    time_limit = 300
    fps = 60

    def __init__(self):
        self._monkeypatch_pygame()

        pygame.init()
        pygame.font.init()

        # Create a base surface with the original game size and the true screen
        self.screen = pygame.Surface((self.screen_width, self.screen_height))
        self._screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE,
        )

        # Restrict the events to process
        pygame.event.set_allowed(
            [
                pygame.QUIT,
                pygame.KEYDOWN,
                pygame.KEYUP,
                pygame.FINGERDOWN,
                pygame.FINGERUP,
            ]
        )

        # Track window size
        self.window_width = self.screen_width
        self.window_height = self.screen_height

        # Set title and complete initialization
        pygame.display.set_caption("Skyfall")

        self.fonts = self._load_fonts()
        self.images = self._load_images()
        self.colors = self._create_colors()

        self.clock = pygame.time.Clock()
        self.delta_time = self.clock.tick(self.fps) / 1000

    def handle_rescale(self, width, height):
        self.window_width = max(width, self.screen_width - 400)
        self.window_height = max(height, self.screen_height - 400)
        pygame.display.set_mode(
            (self.window_width, self.window_height), pygame.RESIZABLE
        )
        self.calculate_scaled_size()

    def calculate_scaled_size(self):
        aspect_ratio = self.screen_width / self.screen_height
        window_aspect_ratio = self.window_width / self.window_height

        if window_aspect_ratio > aspect_ratio:
            self.scaled_height = self.window_height
            self.scaled_width = int(self.scaled_height * aspect_ratio)
        else:
            self.scaled_width = self.window_width
            self.scaled_height = int(self.scaled_width / aspect_ratio)

    def update_display(self):
        scaled = pygame.transform.scale(
            self.screen, (self.scaled_width, self.scaled_height)
        )

        offset_x = (self.window_width - self.scaled_width) // 2
        offset_y = (self.window_height - self.scaled_height) // 2

        self._screen.fill(self.colors.black)
        self._screen.blit(scaled, (offset_x, offset_y))

        pygame.display.flip()
        self.delta_time = self.clock.tick(self.fps) / 1000

    #
    # Initialization methods
    #
    def _create_colors(self):
        class colors:
            black = (0, 0, 0)
            white = (255, 255, 255)
            grey = (100, 100, 100)
            sky_blue = (135, 206, 235)
            red = (139, 0, 0)
            orange = (255, 165, 0)
            blue = (0, 0, 139)
            green = (0, 100, 0)

        return colors

    def _monkeypatch_pygame(self):
        """
        For reasons I don't fully understand, pygame crashbombs when used with
        certain joysticks, including the one that is used for this game, which means
        we have to disable joystick support, and use keyboard mapping outside of
        the game to use the joystick.
        """

        def _fake_init(*a, **k):
            pass

        pygame.joystick.init = _fake_init

    def _load_fonts(self):
        """
        Collection of standard fonts used throughout the game.
        """

        class fonts:
            title = pygame.font.Font(resource("fonts/title.ttf"), 144)
            leaderboard_title = pygame.font.Font(resource("fonts/title.ttf"), 50)
            hud = pygame.font.Font(resource("fonts/common.otf"), 20)
            common = pygame.font.Font(resource("fonts/common.otf"), 36)
            small_common = pygame.font.Font(
                resource("fonts/common.otf"), int(36 * 0.75)
            )
            inputs = pygame.font.Font(resource("fonts/common.otf"), int(36 * 0.75))
            errors = pygame.font.Font(resource("fonts/common.otf"), int(36 * 0.6))

        return fonts

    def _load_images(self):
        """
        Collection of standard images used throughout the game
        """

        class images:
            player = pygame.image.load(resource("images/skydiver.png")).convert_alpha()
            mission = pygame.image.load(resource("images/mission.png")).convert_alpha()
            dynamic_o = pygame.image.load(
                resource("images/dynamic-o.png")
            ).convert_alpha()
            highscore = pygame.image.load(
                resource("images/highscore.png")
            ).convert_alpha()
            heart_full = pygame.transform.scale(
                pygame.image.load(resource("images/heart-full.png")).convert_alpha(),
                (50, 50),
            )
            heart_empty = pygame.transform.scale(
                pygame.image.load(resource("images/heart-empty.png")).convert_alpha(),
                (50, 50),
            )
            cloud_a = pygame.image.load(resource("images/cloud1.png")).convert_alpha()
            cloud_b = pygame.image.load(resource("images/cloud2.png")).convert_alpha()
            cloud_c = pygame.image.load(resource("images/cloud3.png")).convert_alpha()
            helicopter = pygame.transform.scale(
                pygame.image.load(resource("images/helicopter.png")).convert_alpha(),
                (100, 50),  # size of helicopter
            )
            explosion = pygame.image.load(
                resource("images/explosion.png")
            ).convert_alpha()

        return images

    #
    # Utility methods
    #
    async def render_text(self, text, font, color, center_x, center_y):
        """
        Render text using a specific font, color, and central position.
        """

        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(center_x, center_y))
        game.screen.blit(text_surface, text_rect)

    #
    # View methods
    #

    async def show_title(self):
        """
        Show the "title screen" for the game.
        """

        return await TitleView().run()

    async def show_session_info(self):
        """
        Show the "session info" screen, which collects and validates information
        about the player for their gaming session.
        """

        return await SessionInfoView().run()

    async def show_game(self, lives):
        """
        Show the "game screen" for the game itself.
        """

        return await GameView(lives=lives).run()

    async def show_end_of_life(self, score, time_survived, cloud_points, max_speed):
        """
        Show the "end of life" screen, which summarizes the score of a "life."
        """

        return await EndOfLifeView(score, time_survived, cloud_points, max_speed).run()

    async def show_end_of_round(self, scores, name, email):
        """
        Show the "end of round" screen, which summarizes the player's full gaming
        session, including their scores and where they land on the leaderboard.
        """

        return await EndOfRoundView(scores, name, email).run()

    async def play(self, name="", email=""):
        """
        Initiate a gaming session for a player with the provided name and email. If
        the game is being played in a web browser, name and email will be empty.
        """

        scores = []
        lives = game.total_lives

        if not BROWSER:
            # Check if the player exists, and register them if not
            leaderboard.add_player(email, name)

            # Log the start of a new session
            session_start = datetime.now()

        # Give the user three "lives", recording the scores for later, and displaying
        # an end-of-life screen to summarize the "life"
        while lives > 0:
            session = await self.show_game(lives)
            score, time_survived, cloud_points, max_speed = await session.get_results()
            scores.append(score)

            await self.show_end_of_life(score, time_survived, cloud_points, max_speed)
            lives -= 1

        if not BROWSER:
            # Log the session at the end
            session_end = datetime.now()
            leaderboard.log_session(email, session_start, session_end, scores)

        # Display an end of round screen before returning to the title screen
        await self.show_end_of_round(scores, name, email)


# Create an instance of SkyfallGame for the rest of the code to use
game = SkyfallGame()


#
# Game views
#


class View:
    """
    Base class for building out each distinct view within the game. It provides
    shared utility methods, and orchestrates the main loop and event loop.
    """

    async def display_brand_symbol(self):
        """
        Render the Mission "Dynamic O" mark in the bottom right of the screen
        """

        dynamic_o_scaled = pygame.transform.scale(
            game.images.dynamic_o,
            (
                int(game.images.dynamic_o.get_width() * 0.15),
                int(game.images.dynamic_o.get_height() * 0.15),
            ),
        )
        symbol_x = game.screen_width - dynamic_o_scaled.get_width() - 20
        symbol_y = game.screen_height - dynamic_o_scaled.get_height() - 20
        game.screen.blit(dynamic_o_scaled, (symbol_x, symbol_y))

    async def draw(self):
        """
        Subclasses of `View` must provide a `draw` method, which is called on each
        iteration of the main loop of the game. Subclasses do not need to worry about
        building the loop itself, updating the display, advancing the clock, etc.
        """

        raise NotImplementedError()

    async def handle_event(self, event):
        """
        Subclasses of `View` must provide a `handle_event` method, which will be
        called as events flow in from pygame, including things like key presses,
        etc. Subclasses do not need to worry about building an event loop.
        """

        raise NotImplementedError()

    async def stop(self):
        """
        Stops the run loop for the view.
        """

        self.running = False

    async def run(self):
        """
        Main run loop and event loop for the view. Handles the coordination of view
        rendering, event handling, and run state. When the run loop is complete,
        the method returns `self`, which can be used to fetch state from the end of
        the run loop, such as game scores, player information, etc.
        """

        self.running = True
        frame_count = 0
        while self.running:
            frame_count += 1

            # Call the subclass' `draw` method to paint the screen
            await self.draw()

            # Handle events from pygame
            if frame_count % 2 == 0:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        sys.exit()

                    if event.type == pygame.VIDEORESIZE:
                        game.handle_rescale(event.w, event.h)

                    await self.handle_event(event)

                pygame.event.pump()

            # Tell pygame to update the display, and yield to other tasks
            game.update_display()
            await asyncio.sleep(0)

        return self


class TitleView(View):
    """
    Title screen for the game. Shows the name of the game, the leaderboard, some
    branding, and instructions.
    """

    def __init__(self):
        super().__init__()

        self._max_skydiver_movement = 200
        self._skydiver_pos = game.screen_width // 2
        self._skydiver_direction = 1
        self._blink_timer = 0
        self._blink_interval = 3000
        self._background_clouds = []
        self._populate_clouds()
        self._leaderboard = Leaderboard()

    async def handle_event(self, event):
        """
        Handle pygame events on the title screen, which allow the user to proceed
        to the session info view and then start the game.
        """

        # If the user presses 'Return', go to session info screen
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await game.show_session_info()

        # If the user is on mobile and taps the screen, go to session into screen
        elif BROWSER and event.type == pygame.FINGERUP:
            await game.show_session_info()
            return

    async def draw(self):
        """
        Draw method for the title screen, called once per cycle of the main loop.
        """

        # Draw background color of the sky
        game.screen.fill(game.colors.sky_blue)

        # Draw title
        await game.render_text(
            "SKYFALL", game.fonts.title, game.colors.white, game.screen_width // 2, 200
        )

        # Draw remainder of title screen
        await self._draw_clouds()
        await self._leaderboard.draw()
        await self._draw_skydiver()
        await self._draw_message()
        await self._draw_brand_and_message()

    async def _draw_brand_and_message(self):
        """
        Draw the Mission logo and a message that the game was built by Mission.
        """

        mission_scaled = pygame.transform.scale(
            game.images.mission,
            (
                int(game.images.mission.get_width() * 0.45),
                int(game.images.mission.get_height() * 0.45),
            ),
        )

        await game.render_text(
            "BROUGHT TO YOU BY",
            game.fonts.small_common,
            game.colors.black,
            game.screen_width // 2,
            game.screen_height - 180,
        )
        game.screen.blit(
            mission_scaled,
            (
                round((game.screen_width - mission_scaled.get_width()) // 2),
                round(game.screen_height - 60 - mission_scaled.get_height()),
            ),
        )

    async def _draw_skydiver(self):
        """
        Draw the skydiver, who will float left and right on the screen under the title
        """

        # Draw the skydiver
        skydiver_size = 100
        game.screen.blit(
            game.images.player,
            (round(self._skydiver_pos - skydiver_size // 2), round(350)),
        )

        # Animate skydiver position, reversing if needed
        move_speed = 5
        self._skydiver_pos += move_speed * self._skydiver_direction * game.delta_time

        if self._skydiver_pos < (
            game.screen_width // 2 - self._max_skydiver_movement
        ) or self._skydiver_pos > (
            game.screen_width // 2 + self._max_skydiver_movement
        ):
            self._skydiver_direction *= -1

    async def _draw_message(self):
        """
        Draw blinking text that tells the player how to start the game
        """

        self._blink_timer += game.delta_time * 1000
        if self._blink_timer >= self._blink_interval:
            self._blink_timer = 0

        if self._blink_timer < self._blink_interval / 2:
            message = "Press ENTER or TOUCH to play"
            await game.render_text(
                message,
                game.fonts.common,
                game.colors.red,
                game.screen_width // 2,
                550,
            )

    def _populate_clouds(self):
        """
        Randomly add five clouds moving at random speeds to the title screen.
        """

        for _ in range(5):
            cloud_type = random.randint(0, 2)
            cloud_speed = random.uniform(50, 150)
            self._background_clouds.append(BackgroundCloud(cloud_type, cloud_speed))

    async def _draw_clouds(self):
        """
        Draw background clouds, re-populating with additional clouds as they exit
        the screen.
        """

        # Move and draw background clouds
        for cloud in self._background_clouds[:]:
            cloud.move(game.delta_time)
            cloud.draw()

            # Remove cloud once it goes off-screen and add a new one
            if cloud.rect.y + cloud.rect.height < 0:
                self._background_clouds.remove(cloud)
                cloud_type = random.randint(0, 2)
                cloud_speed = random.uniform(50, 150)
                self._background_clouds.append(
                    BackgroundCloud(cloud_type, cloud_speed)
                )


class SessionInfoView(View):
    """
    View for collecting player info after the title screen and before the game begins.
    """

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

    async def _set_cursor_timing(self):
        """
        Handle the blinking of the cursor in our input boxes
        """

        self._blink_timer += game.delta_time * 1000
        if self._blink_timer >= 500:
            self._blink_timer = 0
            self._cursor_visible = not self._cursor_visible

    async def _draw_input(self, message, target):
        """
        Draw an input field, with the supplied message, at the supplied target.
        """

        # Draw message
        await game.render_text(
            message,
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            game.screen_height // 3,
        )

        # Draw input box
        input_rect = pygame.Rect(
            round((game.screen_width - self._input_box_width) // 2),
            round(game.screen_height // 3 + 50),
            round(self._input_box_width),
            round(self._input_box_height),
        )
        pygame.draw.rect(game.screen, game.colors.black, input_rect, 1)

        # Render text as the user types
        text = game.fonts.inputs.render(target, True, game.colors.black)
        game.screen.blit(text, (round(input_rect.x + 10), round(input_rect.y + 5)))

        # Show the cursor if visible on this iteration
        if self._cursor_visible:
            cursor_x = round(input_rect.x + 10 + text.get_width() + 2)
            pygame.draw.line(
                game.screen,
                game.colors.black,
                (cursor_x, round(input_rect.y + 5)),
                (cursor_x, round(input_rect.y + 45)),
                2,
            )

    async def _draw_name_input(self):
        await self._draw_input("Enter your name:", self._name)

    async def _draw_email_input(self):
        await self._draw_input("Enter your email:", self._email)

    async def _handle_validation_errors(self):
        """
        In the event that the user inputs invalid information, display an error
        message.
        """

        lines = self._error_message.split("\n")
        for i, line in enumerate(lines):
            await game.render_text(
                line,
                game.fonts.errors,
                game.colors.red,
                game.screen_width // 2,
                game.screen_height // 3 + 120 + i * 30,
            )

    async def draw(self):
        """
        Draw method for the session info screen, called once per iteration of the
        main loop. Will intelligently skip itself and go straight to the game if
        running inside a web browser.
        """

        # Don't bother collecting information if running in the browser
        if BROWSER:
            await game.play()
            return

        # Draw the sky backgro8und
        game.screen.fill(game.colors.sky_blue)

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
        """
        Handle pygame events for the session info screen.
        """

        if event.type != pygame.KEYDOWN:
            return

        if event.key == pygame.K_ESCAPE:
            await game.show_title()
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
                    await game.play(self._name, self._email)
                    return
                else:
                    self._error_message = "Please enter a valid email address."
        else:
            if event.unicode.isprintable():
                if self._is_typing_name and len(self._name) < 30:
                    self._name += event.unicode
                if self._is_typing_email and len(self._email) < 50:
                    self._email += event.unicode

    def _is_valid_email(self, email):
        """
        Validation utility for email addresses.
        """

        pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
        return re.match(pattern, email)


class EndOfLifeView(View):
    """
    After the player completes each of their three "lives," this screen displays a
    summary of their score for that life, including detail about their time survived,
    their points collected from hitting clouds, and their max speed.
    """

    def __init__(self, score, time_survived, cloud_points, max_speed):
        super().__init__()
        self._score = score
        self._time_survived = time_survived
        self._cloud_points = cloud_points
        self._max_speed = max_speed

    async def draw(self):
        game.screen.fill(game.colors.sky_blue)
        await game.render_text(
            f"Score: {round(self._score)}",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            200,
        )
        await game.render_text(
            f"Time Alive: {round(self._time_survived)} seconds",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            300,
        )
        await game.render_text(
            f"Cloud Points: {round(self._cloud_points)}",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            380,
        )
        await game.render_text(
            f"Max Speed: {round(self._max_speed)} ft/s",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            460,
        )
        await game.render_text(
            "Press ENTER or TOUCH to continue",
            game.fonts.common,
            game.colors.red,
            game.screen_width // 2,
            game.screen_height - 200,
        )

        await self.display_brand_symbol()

    async def handle_event(self, event):
        """
        Handle pygame events that allow the player to proceed in their game session
        """

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await self.stop()
        if BROWSER and event.type == pygame.FINGERUP:
            await self.stop()


class EndOfRoundView(View):
    """
    View displaying the results of all three "lives" in the player's gaming session.
    Includes each of their scores, where they land on the leaderboard, and whether
    or not they have the highest score.
    """

    def __init__(self, scores, name, email):
        super().__init__()
        self._scores = sorted(scores, reverse=True)
        self._name = name
        self._email = email
        self._best_score = max(scores)
        self._player_is_top = (
            None if BROWSER else leaderboard.is_high_score(self._best_score)
        )
        self._leaderboard = Leaderboard(self._name, self._scores)

    async def _draw_header(self):
        """
        Draws a header for the view, which will either show the high score image,
        or a simple message that their session has ended.
        """

        # If the player is top, display the highscore.png image
        if self._player_is_top:
            highscore_rect = game.images.highscore.get_rect(
                center=(game.screen_width // 2, 200)
            )
            game.screen.blit(game.images.highscore, highscore_rect)

        # Display "End of Round" if player is not the top scorer
        else:
            await game.render_text(
                "End of Round",
                game.fonts.common,
                game.colors.black,
                game.screen_width // 2,
                200,
            )

    async def _draw_player_scores(self):
        """
        Display the player's scores from this session.
        """

        await game.render_text(
            "Your Scores:",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            300,
        )
        for i, score in enumerate(self._scores):
            await game.render_text(
                f"Score {i + 1}: {round(score)}",
                game.fonts.common,
                game.colors.black,
                game.screen_width // 2,
                360 + i * 60,
            )

    async def draw(self):
        """
        Draw the end of round screen.
        """

        # Draw background
        game.screen.fill(game.colors.sky_blue)

        # Draw header based upon top score
        await self._draw_header()
        await self._draw_player_scores()
        await self._leaderboard.draw()
        await self._draw_summary()
        await self._draw_instructions()
        await self.display_brand_symbol()

    async def _draw_summary(self):
        """
        Draw a quick summary of the player's session
        """

        if BROWSER:
            return

        # Indicate the player's best score and ranking
        top_scores = leaderboard.get_leaderboard(count=8)
        player_rank = None
        for i, (name, score, _) in enumerate(top_scores):
            if (name == self._name) and (score == self._best_score):
                player_rank = i + 1
                break

        if player_rank and not self._player_is_top:
            await game.render_text(
                f"You are ranked {player_rank} with a score of {int(self._best_score)}",
                game.fonts.small_common,
                game.colors.red,
                game.screen_width // 2,
                game.screen_height - 120,
            )

    async def _draw_instructions(self):
        """
        Tell the player how to exit their session and go back to the title screen.
        """

        await game.render_text(
            "Press ENTER or TOUCH to restart",
            game.fonts.common,
            game.colors.black,
            game.screen_width // 2,
            game.screen_height - 200,
        )

    async def handle_event(self, event):
        """
        Handle events as they come in from pyevent, returning to the title screen
        when appropriate.
        """

        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()

        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            await game.show_title()
            return

        if BROWSER and event.type == pygame.FINGERUP:
            await game.show_title()
            return


class GameView(View):
    """
    View for the game itself, which includes the player, helicopters, clouds, a HUD,
    life tracker, and branding.
    """

    def __init__(self, lives):
        super().__init__()
        self._lives = lives
        self._player = Player()
        self._clouds = []
        self._helicopters = []
        self._total_cloud_points = 0
        self._time_survived = 0
        self._obstacle_speed = 200
        self._max_speed = 200
        self._start_time = pygame.time.get_ticks()

        # Flags for tracking continuous touch steering
        self._steer_left = False
        self._steer_right = False

    async def _draw_hud(self):
        """
        Display a HUD in the top left of the screen showing how long they have
        survived, how many cloud points they've collected, and what their current
        fall speed is.
        """

        hud_width = 250
        hud_height = 110

        time_text = game.fonts.hud.render(
            f"Time: {int(self._time_survived)} s", True, game.colors.white
        )
        cloud_text = game.fonts.hud.render(
            f"Cloud Points: {self._total_cloud_points}", True, game.colors.white
        )
        speed_text = game.fonts.hud.render(
            f"Speed: {int(self._obstacle_speed)} ft/s", True, game.colors.white
        )
        hud_surface = pygame.Surface((hud_width, hud_height))
        hud_surface.set_alpha(100)
        hud_surface.fill(game.colors.black)
        game.screen.blit(hud_surface, (10, 10))

        pygame.draw.rect(
            game.screen, game.colors.black, (10, 10, hud_width, hud_height), 1
        )

        game.screen.blit(time_text, (20, 20))
        game.screen.blit(cloud_text, (20, 20 + time_text.get_height() + 4))
        game.screen.blit(speed_text, (20, 20 + 2 * (time_text.get_height() + 4)))

    async def _steer(self):
        """
        Handle requests to steer to the left or right.
        """

        if self._steer_left:
            self._player.handle_movement({pygame.K_LEFT: True})
        elif self._steer_right:
            self._player.handle_movement({pygame.K_RIGHT: True})
        else:
            self._player.handle_movement({})

    async def _populate_clouds_and_helis(self):
        """
        Add clouds and helicopters as needed, with random positions and speeds.
        """

        if random.random() < 0.03:
            cloud_type = random.randint(0, 2)
            self._clouds.append(Cloud(cloud_type, self._obstacle_speed))
        if random.random() < min((0.002 * self._time_survived), 0.02):
            self._helicopters.append(Helicopter(self._obstacle_speed))

    async def _handle_cloud_movement(self):
        """
        Move clouds and see if they have collided with the player.
        """

        for cloud in self._clouds[:]:
            cloud.move(game.delta_time)
            if self._player.rect.colliderect(cloud.rect):
                self._total_cloud_points += cloud.point_value
                self._clouds.remove(cloud)

    async def _handle_helicopter_movement(self):
        """
        Move helicopters and see if they have collided with either the player or
        with each other, causing them to explode.
        """

        for heli in self._helicopters:
            if self._player.hitbox.colliderect(heli.rect) and not heli.exploded:
                self._score = (10 * self._time_survived) + self._total_cloud_points
                await self.stop()
                return

            heli.move(game.delta_time)

            if heli.exploded:
                continue

        for other_heli in self._helicopters:
            if (
                other_heli != heli
                and other_heli.rect.colliderect(heli.rect)
                and not other_heli.exploded
            ):
                heli.exploded = True
                other_heli.exploded = True

    async def _draw_lives(self):
        """
        Draw filled and empty hearts in the top right of the screen, indicating how
        many lives the player has left.
        """

        padding = 20
        for i in range(game.total_lives):
            heart_x = game.screen_width - padding - (i * 60) - 50
            heart_image = (
                game.images.heart_full if i < self._lives else game.images.heart_empty
            )
            game.screen.blit(heart_image, (heart_x, 10))

    async def draw(self):
        """
        Draw the game view on each iteration of the main loop.
        """

        speed_increment = 15

        self._time_survived = (pygame.time.get_ticks() - self._start_time) / 1000

        # Gradually increment speed
        self._obstacle_speed += speed_increment * game.delta_time
        self._max_speed = max(self._max_speed, self._obstacle_speed)

        # End the round if the player has exceeded the time limit
        if self._time_survived > game.time_limit:
            self._score = (10 * self._time_survived) + self._total_cloud_points
            return

        # Handle steering
        await self._steer()

        # Populate the number of clouds and helicopters on screen
        await self._populate_clouds_and_helis()

        # Move and check collisions for clouds and helis
        await self._handle_cloud_movement()
        await self._handle_helicopter_movement()

        # Draw the sky, the player, clouds, and helicopters
        game.screen.fill(game.colors.sky_blue)
        self._player.draw()
        for cloud in self._clouds:
            cloud.draw()
        for helicopter in self._helicopters:
            helicopter.draw()

        # Draw the HUD and number of lives
        await self._draw_hud()
        await self._draw_lives()

        # Show brand symbol (dynamic-o.png) in the bottom right
        await self.display_brand_symbol()

    async def handle_event(self, event):
        """
        Handle events as they come in from pygame, allowing the user to steer the
        skydiver, either with a keyboard or with touch input if on mobile in a web
        browser.
        """

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
        """
        Provide the results of the gaming session once it has concluded.
        """

        return (
            round((10 * self._time_survived) + self._total_cloud_points),
            round(self._time_survived),
            round(self._total_cloud_points),
            round(self._max_speed),
        )


class Player:
    """
    Represents the skydiver that the player is controlling. Supports movement and
    "tilting" in the direction of movement, with acceleration and deceleration
    for realistic steering. Movement speed increases over time.
    """

    def __init__(self):
        self.start_time = pygame.time.get_ticks()
        self.image = pygame.transform.scale(game.images.player, (100, 91))
        self.rect = self.image.get_rect(
            center=(game.screen_width // 2, game.screen_height // 3)
        )

        self.move_speed = 0
        self.base_max_speed = 10  # Initial max speed
        self.base_move_delta = 0.2

        self.angle = 0
        self.max_angle = 15
        self.angle_delta = 0.6

    @property
    def hitbox(self):
        return pygame.Rect(
            self.rect.x + 10,
            self.rect.y + 40,
            self.rect.width - 20,
            self.rect.height - 40,
        )

    @property
    def max_speed(self):
        """
        Dynamically calculate the max speed based on the elapsed game time.
        """
        elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000
        speed_increase = min(
            elapsed_time // 10, 10
        )  # Increase speed every 10 seconds, capped at +5
        return self.base_max_speed + speed_increase

    @property
    def move_delta(self):
        """
        Dynamically calculate the max move delta based on the elapsed game time.
        """
        elapsed_time = (pygame.time.get_ticks() - self.start_time) // 1000

        delta = self.base_move_delta + (0.025 * elapsed_time)
        delta = min(delta, 5)

        return delta

    def move(self, direction):
        """
        Adjust the skydiver's velocity and angle based on the input direction,
        respecting screen boundaries.
        """
        # Moving right
        if direction > 0:
            if self.rect.x < game.screen_width - self.rect.width:
                self.move_speed = min(
                    self.max_speed, self.move_speed + self.move_delta
                )
            self.angle = max(-self.max_angle, self.angle - self.angle_delta)

        # Moving left
        elif direction < 0:
            if self.rect.x > 0:
                self.move_speed = max(
                    -self.max_speed, self.move_speed - self.move_delta
                )
            self.angle = min(self.max_angle, self.angle + self.angle_delta)

        # No movement (deceleration)
        else:
            if self.move_speed > 0:
                self.move_speed = max(0, self.move_speed - self.move_delta)
            elif self.move_speed < 0:
                self.move_speed = min(0, self.move_speed + self.move_delta)

            if self.angle > 0:
                self.angle = max(0, self.angle - self.angle_delta)
            elif self.angle < 0:
                self.angle = min(0, self.angle + self.angle_delta)

        # Update position based on the current velocity
        self.rect.x += self.move_speed

        # Clamp position within screen bounds
        if self.rect.x <= 0:
            self.rect.x = 0
            self.move_speed = max(0, self.move_speed)  # Prevent leftward velocity
        elif self.rect.x >= game.screen_width - self.rect.width:
            self.rect.x = game.screen_width - self.rect.width
            self.move_speed = min(0, self.move_speed)  # Prevent rightward velocity

    def handle_movement(self, keys):
        """
        Map key presses to movement directions.
        """
        if keys.get(pygame.K_LEFT):
            self.move(-1)
        elif keys.get(pygame.K_RIGHT):
            self.move(1)
        else:
            self.move(0)  # Gradually decelerate when no keys are pressed

    def draw(self):
        """
        Draw the player on the screen with the correct rotation.
        """
        # Rotate the image based on the current rotation angle
        rotated_image = pygame.transform.rotate(self.image, self.angle)
        rotated_rect = rotated_image.get_rect(center=self.rect.center)
        game.screen.blit(rotated_image, rotated_rect)


class Cloud:
    """
    Represents a cloud displayed on screen. There are three types of clouds with
    distinct point values and artwork.
    """

    cloud_types = [
        {"image": game.images.cloud_a, "points": 1},
        {"image": game.images.cloud_b, "points": 5},
        {"image": game.images.cloud_c, "points": 10},
    ]

    def __init__(self, cloud_type, speed):
        self.image = self.cloud_types[cloud_type]["image"]
        self.rect = self.image.get_rect()
        self.rect.x = random.randint(0, game.screen_width - self.rect.width)
        self.rect.y = game.screen_height
        self.speed = speed
        self.point_value = self.cloud_types[cloud_type]["points"]

        # Set the text color based on point value
        self.text_color = {
            1: game.colors.blue,
            5: game.colors.green,
            10: game.colors.red,
        }[self.point_value]

    def move(self, delta_time):
        """
        Move the cloud vertically
        """

        self.rect.y -= self.speed * delta_time

    def draw(self):
        """
        Draw the cloud along with its point value and the appropriate image.
        """

        # Draw the image
        game.screen.blit(self.image, self.rect)

        # Calculate the font size based upon the height of the artwork
        font_size = self.rect.height
        font = pygame.font.Font(resource("fonts/common.otf"), font_size)
        point_text = font.render(str(self.point_value), True, self.text_color)
        point_rect = point_text.get_rect(center=self.rect.center)
        game.screen.blit(point_text, point_rect)


class BackgroundCloud(Cloud):
    """
    A special type of cloud that doesn't have point values. Used on the title screen.
    """

    def draw(self):
        game.screen.blit(self.image, self.rect)


class Helicopter:
    """
    Represents a helicopter displayed during gameplay. Rotates left and right,
    and can explode when colliding with another helicopter.
    """

    def __init__(self, speed):
        self.rect = game.images.helicopter.get_rect()
        self.rect.x = random.randint(0, game.screen_width - self.rect.width)
        self.rect.y = game.screen_height
        self.last_direction_change = 1000
        self.speed = speed
        self.horizontal_speed = random.uniform(40, 120)
        self.direction = random.choice([-1, 1])
        self.exploded = False
        self.opacity = 255

    def move(self, delta_time):
        """
        Move the helicopter, unless the helicopter has exploded, in which case,
        slowly fade out of the display.
        """

        if not self.exploded:
            self.rect.y -= self.speed * delta_time
            self.rect.x += self.horizontal_speed * delta_time * self.direction
            if self.rect.left <= 0 or self.rect.right >= game.screen_width:
                if (pygame.time.get_ticks() - self.last_direction_change) > 1000:
                    self.direction *= -1
                    self.last_direction_change = pygame.time.get_ticks()
        else:
            self.rect.y -= 200 * delta_time
            self.opacity = max(0, self.opacity - 51 * delta_time)

    def draw(self):
        """
        Draw the helicopter. Will render the helicopter image in the orientation of
        movement, and will use explosion artwork if the helicopter has collided with
        another.
        """

        if self.exploded:
            game.images.explosion.set_alpha(int(self.opacity))
            game.screen.blit(game.images.explosion, self.rect)
        else:
            image_to_draw = (
                game.images.helicopter
                if self.direction == -1
                else pygame.transform.flip(game.images.helicopter, True, False)
            )
            game.screen.blit(image_to_draw, self.rect)


class Leaderboard:

    box_opacity = 40
    box_width = game.screen_width - 100
    box_height = 240 if BROWSER else 400
    box_y = 680 if BROWSER else game.screen_height - box_height - 250

    def __init__(self, name=None, scores=None):
        self._name = name
        self._scores = scores
        self._blink_on = bool(scores)
        self._blink_interval = 500
        self._blink_timer = 0

    async def _update_blink(self):
        """
        Manage blinking for player scores on the leaderboard
        """

        self._blink_timer += game.delta_time * 1000
        if self._blink_timer >= self._blink_interval:
            self._blink_timer = 0
            self._blink_on = not self._blink_on

    async def draw(self):
        """
        Draw the leaderboard, contextually displaying either the leaderboard itself
        or a message depending on whether the user is running the game in a browser
        """

        # Update blink status if necessary
        if self._scores:
            await self._update_blink()

        # Create a semi-transparent black box for the leaderboard
        leaderboard_box = pygame.Surface((self.box_width, self.box_height))
        leaderboard_box.set_alpha(self.box_opacity)
        leaderboard_box.fill(game.colors.black)
        game.screen.blit(
            leaderboard_box,
            ((game.screen_width - self.box_width) // 2, self.box_y),
        )

        # Draw a message instead of the leaderboard if running in the browser
        message = "Win a Sony PS5 Pro!" if BROWSER else "High Scores"

        # Draw title
        await game.render_text(
            message,
            game.fonts.leaderboard_title,
            game.colors.white,
            game.screen_width // 2,
            self.box_y + 50,
        )

        if BROWSER:
            await game.render_text(
                "\n".join([" Visit booth #1954", "Highest score wins!"]),
                game.fonts.small_common,
                game.colors.black,
                game.screen_width // 2,
                self.box_y + 170,
            )
            return

        # Define leaderboard positions
        leaderboard_start_y = game.screen_height - self.box_height - 160
        line_height = 35

        # Display top scores, highlighting session scores in red with blinking effect
        # if session scores are provided
        top_scores = leaderboard.get_leaderboard(count=8)
        for i, (name, score, _) in enumerate(top_scores):
            if not score:
                text = game.fonts.small_common.render(name, True, game.colors.white)
                game.screen.blit(text, (100, leaderboard_start_y + i * line_height))
                continue

            rank = f"{i + 1}."
            player_name = name if len(name) < 25 else name[:23] + "..."
            score_str = str(int(score)) if score else ""

            # Determine if this score is part of the current session
            color = game.colors.white
            if self._blink_on and self._name == name and score in self._scores:
                color = game.colors.red

            # Right-align rank numbers
            rank_text = game.fonts.small_common.render(rank, True, color)
            game.screen.blit(rank_text, (100, leaderboard_start_y + i * line_height))

            # Left-align player names
            name_text = game.fonts.small_common.render(player_name, True, color)
            game.screen.blit(name_text, (160, leaderboard_start_y + i * line_height))

            # Left-align scores
            score_text = game.fonts.small_common.render(score_str, True, color)
            game.screen.blit(score_text, (650, leaderboard_start_y + i * line_height))


if __name__ == "__main__":
    asyncio.run(game.show_title())

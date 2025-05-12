import pygame
import random
import sys
import numpy as np

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)
RED = (255, 0, 0)
BLUE = (0, 0, 255)  # For invaders
YELLOW = (255, 255, 0)  # Player bullets
CYAN = (0, 255, 255)  # Invader bullets

# Player properties
PLAYER_WIDTH = 50
PLAYER_HEIGHT = 20  # A flat ship
PLAYER_SPEED = 4  # Reduced for NES slower movement
PLAYER_LIVES = 3

# Bullet properties
BULLET_WIDTH = 5
BULLET_HEIGHT = 15
BULLET_SPEED = 6  # Reduced for slower bullets

# Enemy properties
ENEMY_COLS = 10
ENEMY_ROWS = 5
ENEMY_SPACING_X = 60
ENEMY_SPACING_Y = 40
ENEMY_WIDTH = 40
ENEMY_HEIGHT = 20
ENEMY_MOVE_SPEED_X = 1  # Reduced for slower horizontal movement
ENEMY_MOVE_DOWN_STEP = 10  # How much they drop
ENEMY_SHOOT_CHANCE = 0.001  # Reduced for less frequent shooting
ENEMY_MOVE_INTERVAL = 500  # Milliseconds between enemy movement updates (NES-like stepping)

# --- Sound Engine ---
class SoundEngine:
    def __init__(self):
        self.sample_rate = 44100
        self.sounds = {}
        self.generate_sounds()

    def generate_sine_wave(self, freq, duration, amplitude=0.5):
        """Generate a sine wave for smooth sounds."""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        wave = amplitude * np.sin(2 * np.pi * freq * t)
        return (wave * 32767).astype(np.int16)

    def generate_square_wave(self, freq, duration, amplitude=0.5):
        """Generate a square wave for retro NES-like sounds."""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        wave = amplitude * np.sign(np.sin(2 * np.pi * freq * t))
        return (wave * 32767).astype(np.int16)

    def generate_descending_square_wave(self, start_freq, end_freq, duration, amplitude=0.5):
        """Generate a descending square wave for explosion sounds."""
        samples = int(self.sample_rate * duration)
        t = np.linspace(0, duration, samples, False)
        freqs = np.linspace(start_freq, end_freq, samples)
        wave = amplitude * np.sign(np.sin(2 * np.pi * freqs * t))
        return (wave * 32767).astype(np.int16)

    def generate_sounds(self):
        """Generate all sound effects."""
        # Player shoot: High-pitched sine wave
        player_shoot_wave = self.generate_sine_wave(freq=880, duration=0.1)
        self.sounds['player_shoot'] = pygame.mixer.Sound(player_shoot_wave)

        # Enemy shoot: Lower-pitched square wave
        enemy_shoot_wave = self.generate_square_wave(freq=440, duration=0.15)
        self.sounds['enemy_shoot'] = pygame.mixer.Sound(enemy_shoot_wave)

        # Enemy destroyed: Descending square wave
        enemy_destroyed_wave = self.generate_descending_square_wave(start_freq=880, end_freq=440, duration=0.2)
        self.sounds['enemy_destroyed'] = pygame.mixer.Sound(enemy_destroyed_wave)

        # Player hit: Low-frequency square wave
        player_hit_wave = self.generate_square_wave(freq=220, duration=0.3)
        self.sounds['player_hit'] = pygame.mixer.Sound(player_hit_wave)

    def play(self, sound_name):
        """Play a sound by name."""
        if sound_name in self.sounds:
            self.sounds[sound_name].play()

# --- Classes ---

class Player(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.image = pygame.Surface([PLAYER_WIDTH, PLAYER_HEIGHT])
        self.image.fill(GREEN)
        # Make it a bit more ship-like
        pygame.draw.polygon(self.image, GREEN, [(0, PLAYER_HEIGHT), (PLAYER_WIDTH // 2, 0), (PLAYER_WIDTH, PLAYER_HEIGHT)])
        self.image.set_colorkey(BLACK)  # Make background transparent
        
        self.rect = self.image.get_rect()
        self.rect.x = (SCREEN_WIDTH - PLAYER_WIDTH) // 2
        self.rect.y = SCREEN_HEIGHT - PLAYER_HEIGHT - 20
        self.speed_x = 0
        self.lives = PLAYER_LIVES
        self.shoot_delay = 250  # milliseconds
        self.last_shot_time = pygame.time.get_ticks()

    def update(self):
        self.speed_x = 0
        keystate = pygame.key.get_pressed()
        if keystate[pygame.K_LEFT] or keystate[pygame.K_a]:
            self.speed_x = -PLAYER_SPEED
        if keystate[pygame.K_RIGHT] or keystate[pygame.K_d]:
            self.speed_x = PLAYER_SPEED
        
        self.rect.x += self.speed_x
        if self.rect.left < 0:
            self.rect.left = 0
        if self.rect.right > SCREEN_WIDTH:
            self.rect.right = SCREEN_WIDTH

    def shoot(self, all_sprites, player_bullets, sound_engine):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > self.shoot_delay:
            self.last_shot_time = now
            bullet = Bullet(self.rect.centerx, self.rect.top, -1, YELLOW)  # -1 for up
            all_sprites.add(bullet)
            player_bullets.add(bullet)
            sound_engine.play('player_shoot')

class Enemy(pygame.sprite.Sprite):
    def __init__(self, x, y, enemy_type=0):
        super().__init__()
        self.image = pygame.Surface([ENEMY_WIDTH, ENEMY_HEIGHT])
        self.image.set_colorkey(BLACK)  # Important for drawing complex shapes
        
        # Draw some simple alien shapes
        if enemy_type % 3 == 0:
            color = (200, 50, 50)  # Reddish
            pygame.draw.rect(self.image, color, (0, 0, ENEMY_WIDTH, ENEMY_HEIGHT))
            pygame.draw.rect(self.image, WHITE, (ENEMY_WIDTH*0.2, ENEMY_HEIGHT*0.2, ENEMY_WIDTH*0.2, ENEMY_HEIGHT*0.2))  # Eye 1
            pygame.draw.rect(self.image, WHITE, (ENEMY_WIDTH*0.6, ENEMY_HEIGHT*0.2, ENEMY_WIDTH*0.2, ENEMY_HEIGHT*0.2))  # Eye 2
        elif enemy_type % 3 == 1:
            color = (50, 200, 50)  # Greenish
            pygame.draw.ellipse(self.image, color, (0, 0, ENEMY_WIDTH, ENEMY_HEIGHT))
            pygame.draw.rect(self.image, BLACK, (ENEMY_WIDTH*0.4, ENEMY_HEIGHT*0.4, ENEMY_WIDTH*0.2, ENEMY_HEIGHT*0.2))  # Mouth
        else:
            color = (50, 50, 200)  # Bluish
            points = [(0, ENEMY_HEIGHT), (ENEMY_WIDTH//2, 0), (ENEMY_WIDTH, ENEMY_HEIGHT), (ENEMY_WIDTH*0.75, ENEMY_HEIGHT*0.75), (ENEMY_WIDTH*0.25, ENEMY_HEIGHT*0.75)]
            pygame.draw.polygon(self.image, color, points)

        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y

    def shoot(self, all_sprites, enemy_bullets_group, sound_engine):
        bullet = Bullet(self.rect.centerx, self.rect.bottom, 1, CYAN)  # 1 for down
        all_sprites.add(bullet)
        enemy_bullets_group.add(bullet)
        sound_engine.play('enemy_shoot')

class Bullet(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, color):
        super().__init__()
        self.image = pygame.Surface([BULLET_WIDTH, BULLET_HEIGHT])
        self.image.fill(color)
        self.rect = self.image.get_rect()
        self.rect.centerx = x
        self.rect.centery = y
        if direction == -1:  # Player bullet starts from top
            self.rect.bottom = y
        else:  # Enemy bullet starts from bottom
            self.rect.top = y

        self.speed_y = BULLET_SPEED * direction

    def update(self):
        self.rect.y += self.speed_y
        if self.rect.bottom < 0 or self.rect.top > SCREEN_HEIGHT:
            self.kill()

# --- Game Functions ---

def create_enemies(all_sprites, enemies_group):
    print("Creating enemies!")
    enemies_group.empty()
    start_x = (SCREEN_WIDTH - (ENEMY_COLS * ENEMY_SPACING_X)) // 2 + ENEMY_SPACING_X // 2 - ENEMY_WIDTH // 2
    start_y = 50
    for row in range(ENEMY_ROWS):
        for col in range(ENEMY_COLS):
            x = start_x + col * ENEMY_SPACING_X
            y = start_y + row * ENEMY_SPACING_Y
            enemy_type = row
            enemy = Enemy(x, y, enemy_type)
            all_sprites.add(enemy)
            enemies_group.add(enemy)
    return enemies_group

def display_text(surface, text, size, x, y, color=WHITE):
    font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    text_rect.midtop = (x, y)
    surface.blit(text_surface, text_rect)

def game_over_screen(screen, score):
    screen.fill(BLACK)
    display_text(screen, "GAME OVER!", 64, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4, RED)
    display_text(screen, f"Final Score: {score}", 40, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    display_text(screen, "Press R to Restart or Q to Quit", 30, SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3 // 4)
    pygame.display.flip()
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    waiting_for_input = False
        pygame.time.Clock().tick(15)

def win_screen(screen, score):
    screen.fill(BLACK)
    display_text(screen, "YOU WON!", 50, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 4, GREEN)
    display_text(screen, f"Final Score: {score}", 40, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
    display_text(screen, "Press R to Play Again or Q to Quit", 30, SCREEN_WIDTH // 2, SCREEN_HEIGHT * 3 // 4)
    pygame.display.flip()
    waiting_for_input = True
    while waiting_for_input:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_q:
                    pygame.quit()
                    sys.exit()
                if event.key == pygame.K_r:
                    waiting_for_input = False
        pygame.time.Clock().tick(15)

# --- Main Game Loop ---
def main_game():
    pygame.init()
    pygame.mixer.init(frequency=44100, size=-16, channels=1)  # Mono, 16-bit, 44.1 kHz
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Space Invaders Zero Shot")
    clock = pygame.time.Clock()

    # Initialize sound engine
    sound_engine = SoundEngine()

    # Sprite Groups
    all_sprites = pygame.sprite.Group()
    enemies_group = pygame.sprite.Group()
    player_bullets = pygame.sprite.Group()
    enemy_bullets = pygame.sprite.Group()

    player = Player()
    all_sprites.add(player)

    create_enemies(all_sprites, enemies_group)
    
    score = 0
    enemy_current_move_speed_x = ENEMY_MOVE_SPEED_X
    move_enemies_down = False
    last_enemy_move_time = pygame.time.get_ticks()

    running = True
    game_state = "playing"

    while running:
        dt = clock.tick(FPS) / 1000.0

        # --- Event Handling ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if game_state == "playing":
                    if event.key == pygame.K_SPACE or event.key == pygame.K_UP or event.key == pygame.K_w:
                        player.shoot(all_sprites, player_bullets, sound_engine)
                elif game_state == "game_over" or game_state == "win":
                    if event.key == pygame.K_r:
                        return True
                    if event.key == pygame.K_q:
                        running = False
            
        if game_state != "playing":
            if game_state == "game_over":
                game_over_screen(screen, score)
                return True
            elif game_state == "win":
                win_screen(screen, score)
                return True
            continue

        # --- Updates ---
        all_sprites.update()

        # Enemy movement logic (NES-style stepping)
        if enemies_group:
            now = pygame.time.get_ticks()
            if now - last_enemy_move_time >= ENEMY_MOVE_INTERVAL:
                wall_hit = False
                for enemy in enemies_group:
                    enemy.rect.x += enemy_current_move_speed_x
                    if enemy.rect.right > SCREEN_WIDTH or enemy.rect.left < 0:
                        wall_hit = True
                
                if wall_hit:
                    enemy_current_move_speed_x *= -1
                    move_enemies_down = True
                
                if move_enemies_down:
                    for enemy in enemies_group:
                        enemy.rect.y += ENEMY_MOVE_DOWN_STEP
                        if enemy.rect.bottom >= player.rect.top:
                            player.lives = 0
                            game_state = "game_over"
                            print("Enemies reached the player! GAME OVER!")
                    move_enemies_down = False
                
                last_enemy_move_time = now

        # Enemy shooting
        for enemy in enemies_group:
            if random.random() < ENEMY_SHOOT_CHANCE:
                enemy.shoot(all_sprites, enemy_bullets, sound_engine)

        # --- Collision Detection ---
        # Player bullets hit enemies
        hits = pygame.sprite.groupcollide(enemies_group, player_bullets, True, True)
        for hit_enemy in hits:
            score += 100
            print(f"Enemy destroyed! Score: {score}")
            sound_engine.play('enemy_destroyed')

        # Enemy bullets hit player
        hits = pygame.sprite.spritecollide(player, enemy_bullets, True)
        for hit in hits:
            player.lives -= 1
            print(f"Player hit! Lives left: {player.lives}")
            sound_engine.play('player_hit')
            if player.lives <= 0:
                game_state = "game_over"
                print("Player is dead! GAME OVER!")
                player.kill()

        # Check for win condition
        if not enemies_group and game_state == "playing":
            game_state = "win"
            print("All enemies destroyed! YOU WIN!")

        # --- Drawing ---
        screen.fill(BLACK)
        all_sprites.draw(screen)

        # Display score and lives
        display_text(screen, f"Score: {score}", 30, SCREEN_WIDTH - 100, 10)
        display_text(screen, f"Lives: {player.lives}", 30, 100, 10)

        pygame.display.flip()

    pygame.quit()
    sys.exit()
    return False

if __name__ == '__main__':
    print("Starting the game...")
    while main_game():
        print("Restarting the game...")
    print("Exiting the game. Goodbye!")

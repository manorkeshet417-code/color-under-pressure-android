"""Color Under Pressure on Android: the game runs as is; this layer makes a phone feel right.

- the screen: full screen, landscape, scaled (the game keeps thinking in its own pixels)
- touch: taps are already mouse clicks (SDL does that); where the game wants WASD/arrows,
  an on-screen joystick and an action button appear
- the phone's Back button = ESC
- the phone keyboard: a small keyboard button opens it; what you type arrives like key presses
- Hebrew: the phone's own Noto Sans Hebrew font
- links open in the phone's browser, HTTPS works (certifi), saves live outside the app folder

On a computer, CUP_FAKE_ANDROID=1 turns the same layer on (the mouse plays the finger) for testing.
"""
import os, time, math, glob

REAL = 'ANDROID_ARGUMENT' in os.environ or 'ANDROID_PRIVATE' in os.environ
ANDROID = REAL or bool(os.environ.get('CUP_FAKE_ANDROID'))
STICK_R = 78


def game_size(w, h):
    """The logical size the game draws at: 720 high, as wide as the phone's screen shape."""
    if not ANDROID:
        return w, h
    if not REAL:
        return 1560, 720                     # a 20:9 phone, for testing on a computer
    try:
        import pygame
        i = pygame.display.Info()
        a, b = max(i.current_w, i.current_h), min(i.current_w, i.current_h)
        if a > 0 and b > 0:
            return max(900, int(round(720 * a / b))), 720
    except Exception:
        pass
    return 1560, 720


class _State:
    keys_virtual = set()   # key codes "held" by the joystick / action button
    want_move = 0.0        # last time the game asked about walking keys
    pending = []           # events to add to the next get()
    stick = None           # {'id', 'cx', 'cy'} while a finger holds the joystick
    action = None          # pointer id holding the action button
    on_control = set()     # pointers that started on a control
    fingers = []           # fingers down, in order; the first one drives SDL's emulated mouse
    kb_open = False
    kb_auto = False         # opened by us because a text box appeared
    field_t = 0.0           # last time the game drew a text box
    field_rect = None
    frame_fields = []       # text boxes drawn in this frame: (rect, active)
    last_fields = []        # ... in the last finished frame
    want_field = None       # {'rect', 't', 'tries'}: the box the player tapped, until it becomes active
    field_gone_since = 1.0


S = _State()


def install():
    if not ANDROID:
        return
    os.environ.setdefault('SDL_ANDROID_TRAP_BACK_BUTTON', '1')
    import pygame

    # HTTPS: Python on Android has no system certificate store, so use certifi's
    try:
        import certifi
        os.environ.setdefault('SSL_CERT_FILE', certifi.where())
    except Exception:
        pass

    # ---- the screen ----
    _set_mode = pygame.display.set_mode

    def set_mode(size=(0, 0), flags=0, *a, **k):
        flags = (flags & ~pygame.RESIZABLE) | pygame.SCALED
        if REAL:
            flags |= pygame.FULLSCREEN
        surf = _set_mode(size, flags, *a, **k)
        if REAL:
            try:
                pygame.key.stop_text_input()          # the keyboard opens only when asked
            except Exception:
                pass
        return surf
    pygame.display.set_mode = set_mode
    pygame.display.toggle_fullscreen = lambda *a: 0

    # ---- keys the game reads as "held" ----
    move_keys = {pygame.K_a, pygame.K_d, pygame.K_s, pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN}
    _get_pressed = pygame.key.get_pressed

    class Pressed:
        def __init__(self, real):
            self.real = real

        def __getitem__(self, k):
            if k in move_keys:
                S.want_move = time.time()
            try:
                r = self.real[k]
            except Exception:
                r = False
            return bool(r) or k in S.keys_virtual

        def __len__(self):
            return len(self.real)
    pygame.key.get_pressed = lambda: Pressed(_get_pressed())

    _mouse_pressed = pygame.mouse.get_pressed

    def mouse_pressed(*a, **k):
        r = _mouse_pressed(*a, **k)
        return tuple(False for _ in r) if _primary_on_control() else r
    pygame.mouse.get_pressed = mouse_pressed

    # ---- events: controls, Back, keyboard text ----
    _get = pygame.event.get

    def get(*a, **k):
        evs = _get(*a, **k)
        if a or k:
            return evs
        out, typed = [], set()
        for e in evs:
            r = _handle(e, typed)
            out.extend([e] if r is None else r)
        if S.pending:
            out.extend(S.pending)
            S.pending = []
        return out
    pygame.event.get = get

    # ---- the controls are drawn on top of every frame ----
    _flip, _update = pygame.display.flip, pygame.display.update

    def flip(*a, **k):
        _draw_overlay()
        return _flip(*a, **k)

    def update(*a, **k):
        _draw_overlay()
        return _update(*a, **k)
    pygame.display.flip = flip
    pygame.display.update = update

    # ---- Hebrew: the phone's Noto Sans Hebrew ----
    _match = pygame.font.match_font
    he = sorted(glob.glob('/system/fonts/NotoSansHebrew*.ttf'))
    he_bold = [f for f in he if 'Bold' in f]
    he_reg = [f for f in he if 'Regular' in f] or he

    def match_font(name, bold=False, italic=False):
        try:
            p = _match(name, bold, italic)
        except Exception:
            p = None
        if p or not he:
            return p
        n = (name if isinstance(name, str) else ','.join(name)).lower()
        if any(x in n for x in ('arial', 'segoe', 'tahoma', 'calibri', 'david', 'gisha', 'hebrew', 'dejavu',
                                'freesans', 'liberation', 'miriam', 'microsoft')):
            return (he_bold or he_reg)[0] if bold else he_reg[0]
        return None
    pygame.font.match_font = match_font

    # ---- music: if an mp3 can't play here, its .ogg twin can ----
    _load = pygame.mixer.music.load

    def music_load(f, *a, **k):
        try:
            return _load(f, *a, **k)
        except Exception:
            if isinstance(f, str) and f.lower().endswith('.mp3') and os.path.exists(f[:-4] + '.ogg'):
                return _load(f[:-4] + '.ogg', *a, **k)
            raise
    pygame.mixer.music.load = music_load

    # ---- links open in the phone's browser ----
    if REAL:
        import webbrowser

        def open_url(url, *a, **k):
            try:
                from jnius import autoclass
                Intent = autoclass('android.content.Intent')
                Uri = autoclass('android.net.Uri')
                act = autoclass('org.kivy.android.PythonActivity').mActivity
                act.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                return True
            except Exception as ex:
                print('open url failed', ex)
                return False
        webbrowser.open = webbrowser.open_new = webbrowser.open_new_tab = open_url


def text_field(rect, active=True):
    """Called by the game every time it draws a text box (ui_input)."""
    if not ANDROID:
        return
    try:
        r = (rect[0], rect[1], rect[2], rect[3])
    except Exception:
        return
    S.frame_fields.append((r, bool(active)))
    if active or not S.field_rect:
        S.field_rect = r                       # the keyboard button goes next to the active box
    S.field_t = time.time()


def _field_at(pos):
    for r, active in S.last_fields:
        x, y, w, h = r
        if x <= pos[0] <= x + w and y <= pos[1] <= y + h:
            return r, active
    return None, None


def _switch_tick():
    """A tapped box that the game didn't make active by itself gets Tab presses (phones have no Tab key)."""
    import pygame
    wf = S.want_field
    if not wf:
        return
    now = time.time()
    if now - wf['t'] < 0.12:                   # give the game a couple of frames to react to the tap
        return
    active = dict(S.last_fields).get(wf['rect'])
    if active is None or active or wf['tries'] >= 4:
        S.want_field = None
        return
    S.pending.extend(_key_events(pygame.K_TAB, True, '	', 43) + _key_events(pygame.K_TAB, False, '', 43))
    wf['tries'] += 1
    wf['t'] = now


def _field_shown():
    return time.time() - S.field_t < 0.4


def _kb_auto_tick():
    """Open the phone keyboard when a text box shows up, close it when it is gone."""
    now = time.time()
    if _field_shown():
        if S.field_gone_since and not S.kb_open:
            _set_keyboard(True, auto=True)        # a text box just appeared
        S.field_gone_since = 0.0
    else:
        if not S.field_gone_since:
            S.field_gone_since = now
        elif S.kb_open and now - S.field_gone_since > 0.6:
            _set_keyboard(False)


# ---------------------------------------------------------------- controls
def _size():
    import pygame
    s = pygame.display.get_surface()
    return s.get_size() if s else (900, 700)


def _stick_home():
    W, H = _size()
    return 150, H - 150


def _action_home():
    W, H = _size()
    return W - 130, H - 140


def _kb_home():
    """The keyboard button sits right of the text box (None when there is no text box)."""
    if not _field_shown() or not S.field_rect:
        return None
    W, H = _size()
    x, y, w, h = S.field_rect
    if x + w + 40 <= W - 30:
        return x + w + 40, y + h // 2           # right of the box
    return max(30, x - 40), y + h // 2          # no room on the right (box at the screen edge): left of it


def _move_mode():
    return time.time() - S.want_move < 0.5 or S.stick is not None or S.action is not None


def _hit(p, c, r):
    return math.hypot(p[0] - c[0], p[1] - c[1]) <= r


def _primary_on_control():
    """SDL turns the first finger into the mouse; is that finger on one of our controls?"""
    if not REAL:
        return 'mouse' in S.on_control
    return bool(S.fingers) and S.fingers[0] in S.on_control


def _key_events(key, down, unicode='', scancode=0):
    import pygame
    if down:
        return [pygame.event.Event(pygame.KEYDOWN, key=key, mod=0, unicode=unicode, scancode=scancode)]
    return [pygame.event.Event(pygame.KEYUP, key=key, mod=0, unicode='', scancode=scancode)]


def _action(down):
    import pygame
    if down:
        S.keys_virtual |= {pygame.K_SPACE, pygame.K_e}
    else:
        S.keys_virtual -= {pygame.K_SPACE, pygame.K_e}
    return _key_events(pygame.K_SPACE, down, ' ' if down else '', 44) + _key_events(pygame.K_e, down, '', 8)


def _set_stick(dx, dy):
    import pygame
    m = math.hypot(dx, dy)
    on = set()
    if m > STICK_R * 0.32:
        ux, uy = dx / m, dy / m
        if ux < -0.38: on |= {pygame.K_a, pygame.K_LEFT}
        if ux > 0.38: on |= {pygame.K_d, pygame.K_RIGHT}
        if uy < -0.38: on |= {pygame.K_w, pygame.K_UP}
        if uy > 0.38: on |= {pygame.K_s, pygame.K_DOWN}
    S.keys_virtual = on | ({pygame.K_SPACE, pygame.K_e} & S.keys_virtual)


def _pointer(e):
    """(phase, id, (x, y)) for a finger on the phone, or the mouse when testing on a computer."""
    import pygame
    if REAL:
        if e.type in (pygame.FINGERDOWN, pygame.FINGERMOTION, pygame.FINGERUP):
            W, H = _size()
            ph = {pygame.FINGERDOWN: 'down', pygame.FINGERMOTION: 'move', pygame.FINGERUP: 'up'}[e.type]
            return ph, e.finger_id, (e.x * W, e.y * H)
        return None
    if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
        return 'down', 'mouse', e.pos
    if e.type == pygame.MOUSEMOTION:
        return 'move', 'mouse', e.pos
    if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
        return 'up', 'mouse', e.pos
    return None


def _handle(e, typed):
    """None = give the event to the game; a list = give it these events instead."""
    import pygame
    t = e.type

    # Back button = ESC
    back = getattr(pygame, 'K_AC_BACK', None)
    if t in (pygame.KEYDOWN, pygame.KEYUP) and back is not None and e.key == back:
        return _key_events(pygame.K_ESCAPE, t == pygame.KEYDOWN)

    # the phone keyboard sends TEXTINPUT; the game reads KEYDOWN.unicode
    if t == pygame.KEYDOWN and getattr(e, 'unicode', ''):
        typed.add(e.unicode)
    if t == getattr(pygame, 'TEXTINPUT', -1):
        out = []
        for ch in e.text:
            if ch in typed:
                typed.discard(ch)
                continue
            key = ord(ch.lower()) if ch.isascii() and ch.isprintable() else 0
            out += _key_events(key, True, ch) + _key_events(key, False)
        return out

    # on the phone, the emulated mouse of a finger that is on a control is hidden from the game
    if REAL and t in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
        return [] if _primary_on_control() else None

    p = _pointer(e)
    if not p:
        return None
    ph, pid, pos = p
    swallow = [] if not REAL else None        # on the computer the "finger" IS the mouse: hide it
    W, H = _size()

    if ph == 'down':
        if REAL and pid not in S.fingers:
            S.fingers.append(pid)
        kb = _kb_home()
        if kb and _hit(pos, kb, 34):
            S.on_control.add(pid); _set_keyboard(not S.kb_open); return swallow
        if _field_shown():
            r, active = _field_at(pos)
            if r:                                # tapping a text box opens the keyboard and makes it the active one
                if not S.kb_open:
                    _set_keyboard(True)
                if not active:
                    S.want_field = {'rect': r, 't': time.time(), 'tries': 0}
        if _move_mode():
            if S.stick is None and pos[0] < W * 0.42 and pos[1] > H * 0.4:
                sx, sy = _stick_home()
                S.stick = {'id': pid, 'cx': sx, 'cy': sy}
                S.on_control.add(pid); _set_stick(pos[0] - sx, pos[1] - sy)
                return swallow
            if S.action is None and _hit(pos, _action_home(), 75):
                S.action = pid; S.on_control.add(pid)
                evs = _action(True)
                if REAL:
                    S.pending.extend(evs); return None
                return evs
        return None

    if ph == 'move':
        if S.stick and S.stick['id'] == pid:
            _set_stick(pos[0] - S.stick['cx'], pos[1] - S.stick['cy'])
        return swallow if pid in S.on_control else None

    # up
    was = pid in S.on_control
    S.on_control.discard(pid)
    if REAL and pid in S.fingers:
        S.fingers.remove(pid)
    if S.stick and S.stick['id'] == pid:
        S.stick = None; _set_stick(0, 0)
    if S.action == pid:
        S.action = None
        evs = _action(False)
        if REAL:
            S.pending.extend(evs); return None
        return evs
    return swallow if was else None


def _set_keyboard(on, auto=False):
    import pygame
    S.kb_open = on
    S.kb_auto = auto and on
    try:
        if on:
            W, H = _size()
            pygame.key.set_text_input_rect(pygame.Rect(0, H - 80, W, 60))
            pygame.key.start_text_input()
        else:
            pygame.key.stop_text_input()
    except Exception as ex:
        print('keyboard', ex)


_font = {}


def _draw_overlay():
    import pygame
    s = pygame.display.get_surface()
    if s is None:
        return
    try:
        layer = pygame.Surface(s.get_size(), pygame.SRCALPHA)
        S.last_fields, S.frame_fields = S.frame_fields, []
        _switch_tick()
        _kb_auto_tick()
        kb = _kb_home()
        if kb:                                   # keyboard button, next to the text box
            kx, ky = kb
            pygame.draw.circle(layer, (255, 255, 255, 210 if S.kb_open else 150), (kx, ky), 26)
            for i in range(3):
                for j in range(3):
                    pygame.draw.rect(layer, (20, 20, 35, 230), (kx - 13 + j * 9, ky - 10 + i * 7, 7, 5), border_radius=1)
        if _move_mode():
            sx, sy = _stick_home()
            pygame.draw.circle(layer, (255, 255, 255, 45), (sx, sy), STICK_R)
            pygame.draw.circle(layer, (255, 255, 255, 110), (sx, sy), STICK_R, 3)
            dx = 1 if pygame.K_d in S.keys_virtual else -1 if pygame.K_a in S.keys_virtual else 0
            dy = 1 if pygame.K_s in S.keys_virtual else -1 if pygame.K_w in S.keys_virtual else 0
            if dx and dy:
                dx, dy = dx * 0.707, dy * 0.707
            pygame.draw.circle(layer, (255, 255, 255, 150), (int(sx + dx * STICK_R * .55), int(sy + dy * STICK_R * .55)), 34)
            ax, ay = _action_home()
            pygame.draw.circle(layer, (90, 200, 255, 200 if S.action is not None else 110), (ax, ay), 56)
            pygame.draw.circle(layer, (255, 255, 255, 160), (ax, ay), 56, 3)
            f = _font.get('a') or _font.setdefault('a', pygame.font.SysFont(None, 46, bold=True))
            txt = f.render('E', True, (255, 255, 255))
            layer.blit(txt, txt.get_rect(center=(ax, ay)))
        s.blit(layer, (0, 0))
    except Exception as ex:
        print('overlay', ex)

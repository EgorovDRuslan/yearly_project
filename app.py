from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Select, Button, Input, Checkbox, Label, Static, Markdown, LoadingIndicator, OptionList
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen, ModalScreen
from textual import work
import db_manager
import hardware_scanner
import json

class GameCard(Static):
    def __init__(self, name, genre, playtime, date_of_publishing, rating, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_name = name
        self.genre = genre
        self.playtime = playtime if playtime else "N/A"
        self.date_of_publishing = date_of_publishing if date_of_publishing else "TBC"
        self.rating = rating if rating else "TBC"
        self.game_id = game_id

    def compose(self) -> ComposeResult:
        yield Label(f"[b]{self.game_name}[/b]", classes="card-title")
        yield Label(f"[#7aa2f7]PLAYERS (PLAYTIME)[/#7aa2f7] {self.playtime}h   [#7aa2f7]RELEASED[/#7aa2f7] {self.date_of_publishing}   [#7aa2f7]REVIEW SCORE[/#7aa2f7] {self.rating}", classes="card-meta")
        yield Label(f"[#9ece6a]GENRE[/#9ece6a] {self.genre}", classes="card-genre")

class GameItem(ListItem):
    def __init__(self, name, genre, playtime, date_of_publishing, rating, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_data = (name, genre, playtime, date_of_publishing, rating, game_id)
        self.game_id = game_id
        
    def compose(self) -> ComposeResult:
        yield GameCard(*self.game_data)

class GameDetailScreen(Screen):
    BINDINGS = [("escape", "app.safe_pop_screen", "Back")]
    
    def __init__(self, game_id, **kwargs):
        super().__init__(**kwargs)
        self.game_id = game_id
        
    def compose(self) -> ComposeResult:
        game_details = db_manager.get_game_details(self.game_id)
        if game_details:
            name, description, platforms, rating, date_of_publishing, genre = game_details
            
            req_text = ""
            try:
                import re
                pl_data = json.loads(platforms)
                for p in pl_data:
                    req_text += f"\n### {p[0]}\n"
                    req_en = p[1]
                    if isinstance(req_en, dict):
                        for req_type in ['minimum', 'recommended']:
                            req_str = req_en.get(req_type, '')
                            if req_str:
                                req_text += f"- **{req_type.capitalize()}**:\n"
                                parts = re.split(r'(OS:|Processor:|Memory:|Graphics:|Network:|Storage:|DirectX:|Hard Drive:|Sound Card:|Additional Notes:)', req_str)
                                if len(parts) > 1:
                                    idx = 1
                                    while idx < len(parts):
                                        key = parts[idx]
                                        val = parts[idx+1] if idx+1 < len(parts) else ""
                                        val = val.strip().lstrip('<li>').rstrip('</li>').replace('<br>', '').strip()
                                        if val:
                                            req_text += f"  - **{key.strip(':')}**: {val}\n"
                                        idx += 2
                                else:
                                    req_text += f"  - {req_str}\n"
                    else:
                        req_text += f"{req_en}\n"
            except Exception:
                pass
                
            md_content = f"# {name}\n\n"
            md_content += f"**Rating**: {rating} | **Released**: {date_of_publishing} | **Genre**: {genre}\n\n"
            md_content += f"## Description\n{description}\n\n"
            md_content += f"## System Requirements\n{req_text}"
            
            with VerticalScroll(classes="detail-scroll"):
                yield Markdown(md_content)
            yield Footer()
        else:
            yield Label("Game not found.")
            yield Footer()

class ThemeSelectionScreen(ModalScreen):
    BINDINGS = [("escape", "app.safe_pop_screen", "Close")]
    
    def compose(self) -> ComposeResult:
        import textual.theme
        themes = [t for t in textual.theme.BUILTIN_THEMES.keys() if not t.startswith("ansi")]
        themes.sort()
        yield OptionList(*themes, id="theme-modal-list")

    def on_mount(self) -> None:
        theme_list = self.query_one("#theme-modal-list", OptionList)
        import textual.theme
        themes = [t for t in textual.theme.BUILTIN_THEMES.keys() if not t.startswith("ansi")]
        themes.sort()
        try:
            idx = themes.index(self.app.theme)
            theme_list.highlighted = idx
            theme_list.scroll_to_highlight()
        except ValueError:
            pass

    def on_option_list_option_highlighted(self, event: OptionList.OptionHighlighted) -> None:
        if event.option_list.id == "theme-modal-list":
            self.app.theme = str(event.option.prompt)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.app.pop_screen()

class GameRecommenderApp(App):
    CSS_PATH = "styles.tcss"
    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("A", "ai_assistant", "Shift+A (AI Assistant)"),
        ("t", "open_theme_modal", "Themes")
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.hardware_specs = None
        self._is_ready = False

    def compose(self) -> ComposeResult:
        yield Header()
        
        with Horizontal():
            # Left Sidebar
            with VerticalScroll(id="sidebar"):
                yield Label("Hardware Scanner", classes="sidebar-label")
                yield Button("Scan Hardware", id="scan-hardware-btn", variant="primary")
                yield Label("No specs scanned", id="hardware-display", classes="hardware-text")
                
                yield Label("Search games", classes="sidebar-label")
                yield Input(placeholder="Type to search...", id="search-input")
                
                yield Label("Game filter", classes="sidebar-label")
                yield Select([("Show all games", "all")], prompt="Show all games", value="all", id="game-filter")
                
                yield Label("Player count (Playtime)", classes="sidebar-label")
                yield Select([
                    ("Any", "Any"),
                    ("Under 10 hours", "Under 10 hours"),
                    ("10-50 hours", "10-50 hours"),
                    ("Over 50 hours", "Over 50 hours")
                ], value="Any", id="playtime-filter")
                
                yield Label("ESRB Rating", classes="sidebar-label")
                yield Select([
                    ("All", "All"),
                    ("Everyone", "Everyone"),
                    ("Teen", "Teen"),
                    ("Mature", "Mature")
                ], value="All", id="esrb-filter")
                
                yield Button("Reset Filters", id="reset-button", variant="error")
                
                yield Label("Genre", classes="sidebar-label")
                with Vertical(id="genre-checkboxes"):
                    for genre in db_manager.get_all_genres():
                        yield Checkbox(genre, id=f"genre-{genre.replace(' ', '_')}", classes="genre-checkbox")

            # Main Area
            with Vertical(id="main-area"):
                with Horizontal(id="top-bar"):
                    yield Select(
                        [
                            ("Rating", "rating"),
                            ("Name", "name"),
                            ("Playtime", "playtime"),
                            ("Release Date", "date_of_publishing"),
                            ("Genre", "genre"),
                            ("Hardware match", "hardware")
                        ],
                        prompt="Sort by",
                        value="rating",
                        id="sort-select"
                    )
                yield ListView(id="games-list")
                
        yield Footer()

    async def on_mount(self) -> None:
        await self.load_games()
        self.set_timer(0.5, self.enable_ui)

    def enable_ui(self) -> None:
        self._is_ready = True

    async def load_games(self) -> None:
        list_view = self.query_one("#games-list", ListView)
        await list_view.clear()
        
        sort_by = self.query_one("#sort-select", Select).value
        search_text = self.query_one("#search-input", Input).value
        playtime_filter = self.query_one("#playtime-filter", Select).value
        esrb_filter = self.query_one("#esrb-filter", Select).value
        
        selected_genres = [
            cb.label.plain for cb in self.query(Checkbox) if cb.value
        ]
        
        games = db_manager.get_all_games(
            sort_by=sort_by,
            search_text=search_text,
            selected_genres=selected_genres,
            playtime_filter=playtime_filter,
            esrb_filter=esrb_filter,
            hardware_specs=self.hardware_specs
        )
        
        # Limit to 50 games to prevent severe DOM lag during theme switching and scrolling
        items = [GameItem(*game) for game in games[:50]]
        await list_view.extend(items)

    async def on_input_changed(self, event: Input.Changed) -> None:
        if not getattr(self, '_is_ready', False): return
        if event.input.id == "search-input":
            await self.load_games()

    async def on_select_changed(self, event: Select.Changed) -> None:
        if not getattr(self, '_is_ready', False): return
        await self.load_games()

    async def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if not getattr(self, '_is_ready', False): return
        if getattr(self, "_filter_timer", None):
            self._filter_timer.stop()
        self._filter_timer = self.set_timer(1.0, self.load_games)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "reset-button":
            self.query_one("#search-input", Input).value = ""
            self.query_one("#playtime-filter", Select).value = "Any"
            self.query_one("#esrb-filter", Select).value = "All"
            self.query_one("#sort-select", Select).value = "rating"
            for cb in self.query(Checkbox):
                cb.value = False
            await self.load_games()
            
        elif event.button.id == "scan-hardware-btn":
            self.hardware_specs = hardware_scanner.get_hardware_specs()
            display_text = f"OS: {self.hardware_specs['os']}\nCPU: {self.hardware_specs['cpu']}\nGPU: {self.hardware_specs['gpu']}\nRAM: {self.hardware_specs['ram_gb']}GB\nDisk: {self.hardware_specs['disk_gb']}GB"
            self.query_one("#hardware-display", Label).update(display_text)
            self.notify("Hardware scanned! Filtering & Sorting games...", title="Hardware Scanner")
            self.query_one("#sort-select", Select).value = "hardware"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, GameItem):
            self.push_screen(GameDetailScreen(game_id=event.item.game_id))

    def action_ai_assistant(self) -> None:
        self.push_screen(AIAssistantScreen(hardware_specs=self.hardware_specs))

    def action_open_theme_modal(self) -> None:
        self.push_screen(ThemeSelectionScreen())

    def action_safe_pop_screen(self) -> None:
        if len(self.screen_stack) > 1:
            self.pop_screen()

class PacmanLoading(Static):
    DEFAULT_CSS = """
    PacmanLoading {
        color: #e0af68;
        text-style: bold;
        height: 1;
        margin-bottom: 1;
        padding: 0 2;
    }
    """
    FRAMES = [
        "C · · ·",
        "c  · ·",
        "C   ·",
        "c    ",
        "C · · ·",
    ]
    
    def on_mount(self) -> None:
        self.frame_index = 0
        self.interval = self.set_interval(0.2, self.tick)
        self.update(self.FRAMES[0])

    def tick(self) -> None:
        self.frame_index = (self.frame_index + 1) % len(self.FRAMES)
        self.update(self.FRAMES[self.frame_index])

class ChatMessage(Vertical):
    DEFAULT_CSS = "ChatMessage { height: auto; }"
    
    def __init__(self, role, msg_content, is_loading=False, **kwargs):
        super().__init__(**kwargs)
        self.role = role
        self.msg_content = msg_content
        self.is_loading = is_loading
        
    def compose(self) -> ComposeResult:
        if self.role == "user":
            yield Label("[b]You:[/b]", classes="chat-user-name")
        else:
            yield Label("[b]Your Game Geek:[/b]", classes="chat-ai-name")
            
        if self.is_loading:
            yield PacmanLoading(id="loading-anim")
            
        md = Markdown(self.msg_content, classes=f"chat-msg chat-{self.role}")
        if self.is_loading:
            md.styles.display = "none"
        yield md

class AIAssistantScreen(Screen):
    BINDINGS = [
        ("escape", "app.safe_pop_screen", "Back"),
        ("ctrl+q", "ignore", ""),
        ("A", "ignore", "")
    ]
    
    def action_ignore(self):
        pass
        
    def __init__(self, hardware_specs, **kwargs):
        super().__init__(**kwargs)
        self.hardware_specs = hardware_specs
        self.sessions_dict = {}
        self.current_session_id = None
        
    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="chat-container"):
            with VerticalScroll(id="chat-history"):
                pass
            with Horizontal(id="chat-input-area"):
                yield Input(placeholder="Ask AI about games...", id="chat-input")
                yield Button("Send", id="send-msg-btn", variant="primary")
            with Horizontal(id="chat-header"):
                yield Select([], id="chat-session-select")
                yield Button("Delete", id="delete-session-btn", variant="error")
        yield Footer()

    async def on_mount(self) -> None:
        import ai_module
        import uuid
        
        self.sessions_dict = ai_module.load_history()
        
        options = [("New Chat", "new")]
        for sid, sdata in self.sessions_dict.items():
            options.append((sdata.get("title", "Chat"), sid))
            
        select = self.query_one("#chat-session-select", Select)
        select.set_options(options)
        
        self.current_session_id = str(uuid.uuid4())
        select.value = "new"

    async def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id == "chat-session-select":
            import uuid
            
            # Ignore BLANK or any value not in our dictionary (except "new")
            if event.value == type(event.select).BLANK or (event.value != "new" and str(event.value) not in self.sessions_dict):
                return
                
            # Prevent wiping the chat if it's already the active session (e.g. title update)
            if str(event.value) == self.current_session_id:
                return
                
            if event.value == "new":
                self.current_session_id = str(uuid.uuid4())
            else:
                self.current_session_id = str(event.value)
                
            chat_history = self.query_one("#chat-history", VerticalScroll)
            chat_history.remove_children()
            
            if self.current_session_id in self.sessions_dict:
                messages = self.sessions_dict[self.current_session_id].get("messages", [])
                for msg in messages:
                    await chat_history.mount(ChatMessage(msg["role"], msg["content"]))
            chat_history.scroll_end(animate=False)
            
    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "chat-input":
            await self.send_message()
            
    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-msg-btn":
            await self.send_message()
        elif event.button.id == "delete-session-btn":
            await self.delete_session()
            
    async def delete_session(self) -> None:
        if self.current_session_id in self.sessions_dict:
            del self.sessions_dict[self.current_session_id]
            import ai_module
            ai_module.save_history(self.sessions_dict)
            
        import uuid
        self.current_session_id = str(uuid.uuid4())
        
        options = [("New Chat", "new")]
        for sid, sdata in self.sessions_dict.items():
            options.append((sdata.get("title", "Chat"), sid))
            
        select = self.query_one("#chat-session-select", Select)
        select.set_options(options)
        select.value = "new"
        
        chat_history = self.query_one("#chat-history", VerticalScroll)
        chat_history.remove_children()
        
    async def send_message(self) -> None:
        input_widget = self.query_one("#chat-input", Input)
        user_text = input_widget.value.strip()
        if not user_text:
            return
            
        input_widget.value = ""
        chat_history = self.query_one("#chat-history", VerticalScroll)
        
        await chat_history.mount(ChatMessage("user", user_text))
        
        msg_widget = ChatMessage("assistant", "", is_loading=True)
        await chat_history.mount(msg_widget)
        chat_history.scroll_end(animate=False)
        
        needs_title = False
        if self.current_session_id not in self.sessions_dict or not self.sessions_dict[self.current_session_id].get("messages"):
            needs_title = True
        
        self.fetch_ai_response(user_text, msg_widget, needs_title)
        
    @work(thread=True)
    def fetch_ai_response(self, user_text, msg_widget, needs_title):
        import ai_module
        import time
        
        indicator_replaced = [False]
        last_update = [0.0]
        
        def on_chunk(current_text):
            if not indicator_replaced[0]:
                self.app.call_from_thread(self.remove_loading, msg_widget)
                indicator_replaced[0] = True
                
            now = time.time()
            if now - last_update[0] > 0.1:
                self.app.call_from_thread(self.update_msg_widget, msg_widget, current_text)
                last_update[0] = now
            
        result = ai_module.generate_response(self.current_session_id, user_text, self.hardware_specs, chunk_callback=on_chunk)
        
        if not indicator_replaced[0]:
            self.app.call_from_thread(self.remove_loading, msg_widget)
            
        if result:
            self.app.call_from_thread(self.update_msg_widget, msg_widget, result)
        self.app.call_from_thread(self.scroll_to_bottom)
        
        if needs_title:
            new_title = ai_module.generate_chat_title(self.current_session_id, user_text)
            self.app.call_from_thread(self.update_session_title, self.current_session_id, new_title)

    def scroll_to_bottom(self):
        try:
            self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)
        except Exception:
            pass

    def update_session_title(self, session_id, title):
        import ai_module
        self.sessions_dict = ai_module.load_history()
        
        # Ensure session exists in UI dict
        if session_id not in self.sessions_dict:
            self.sessions_dict[session_id] = {"title": title, "messages": []}
            
        options = [("New Chat", "new")]
        for sid, sdata in self.sessions_dict.items():
            options.append((sdata.get("title", "Chat"), sid))
            
        select = self.query_one("#chat-session-select", Select)
        
        self._updating_title = True
        try:
            select.set_options(options)
            
            # Only set if it exists in options
            if any(sid == session_id for _, sid in options):
                select.value = session_id
        finally:
            self._updating_title = False
        
    def remove_loading(self, msg_widget):
        try:
            msg_widget.query_one("#loading-anim").remove()
        except Exception:
            pass

    def update_msg_widget(self, msg_widget, text):
        try:
            md = msg_widget.query_one(Markdown)
            md.styles.display = "block"
            md.update(text)
            self.query_one("#chat-history", VerticalScroll).scroll_end(animate=False)
        except Exception:
            pass

if __name__ == "__main__":
    app = GameRecommenderApp()
    app.run()

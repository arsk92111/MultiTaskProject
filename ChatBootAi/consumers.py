# ChatBootAi/consumers.py
import json
import asyncio
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async 

# Import your existing functions and models
from .views import (
    validate_user_input,
    is_rate_limited,
    rate_limit_phrases,
    get_combined_responses,
    load_responses,
    add_intent_to_json,
    add_response_to_json,
    format_bot_response,
    Conversation,
)

class ChatConsumer(AsyncWebsocketConsumer): 
    chat_group = "live_chatboot"

    async def connect(self): 
        try:
            await self.accept()

            if not await self.authenticate_user():
                return 
            self.user_group = f"user_{self.user.id}"
            await self.channel_layer.group_add(self.user_group, self.channel_name)
 
            await self.channel_layer.group_add(self.chat_group, self.channel_name)
 
            await self.send(json.dumps({
                'type': 'connection_established',
                'message': "Hello! How can I assist you today? I'm! Ready to assist you!"
            }))

            print(f"✅ WebSocket connected: {self.user.email}")

        except Exception as e:
            await self.handle_error("Connection failed", e)

    async def disconnect(self, close_code): 
        try: 
            if hasattr(self, 'user_group'):
                await self.channel_layer.group_discard(self.user_group, self.channel_name)
            await self.channel_layer.group_discard(self.chat_group, self.channel_name)
        except Exception as e:
            print(f"Disconnect error: {e}")

    async def authenticate_user(self): 
        self.user = self.scope["user"]
        if self.user.is_anonymous:
            await self.send_error("Authentication required")
            await self.close(code=4001)
            return False
 
        self.user_email = self.user.email
        return True

    async def receive(self, text_data):
        if self.user.is_anonymous:
            await self.send_error("Authentication required")
            return

        try:
            data = json.loads(text_data)
            action = data.get('action')
            if action == 'send_message':
                await self.handle_message(data)
            elif action == 'get_initial_state':
                await self.send_initial_state()
            elif action is None:
                # No action field → treat as message
                await self.handle_message({'message': data.get('message', '')})
            else:
                await self.send_error("Unknown action")
        except json.JSONDecodeError:
            await self.send_error("Invalid JSON format")
        except Exception as e:
            await self.handle_error("Server error", e)
            
    async def handle_message(self, data): 
        user_input = data.get('message', '').strip()
        if not user_input:
            await self.send_error("Empty message")
            return
 
        if not validate_user_input(user_input):
            await self.send_error("Invalid input")
            return
 
        if await self.is_rate_limited_async() or await self.rate_limit_phrases_async(user_input):
            await self.send_error("Please wait before sending another message.")
            return
 
        await self.send(json.dumps({'type': 'typing', 'status': True}))

        try: 
            loop = asyncio.get_event_loop()
            combined_response = await loop.run_in_executor(
                None,
                get_combined_responses,
                [user_input],
                load_responses(),
                self.user_email
            )
 
            combined_response = self.clean_response(combined_response) 
            await self.save_conversation(user_input, combined_response) 
            await loop.run_in_executor(None, self.add_intent_response, user_input, combined_response)
 
            formatted_response = format_bot_response(combined_response)
 
            await self.send(json.dumps({
                'type': 'bot_response',
                'message': formatted_response,
                'user_input': user_input
            }))

        except Exception as e:
            await self.handle_error("Error processing message", e)
        finally: 
            await self.send(json.dumps({'type': 'typing', 'status': False}))
 
    def clean_response(self, response): 
        response = re.sub(r'\s+', ' ', response).strip()
        response = response.replace("...", " ").replace('....', " ").replace("\n", " ")
        response = response.replace("--", " ").replace("---", " ").replace("----", " ").replace("!!!", "!")
        return response

    def add_intent_response(self, user_input, combined_response): 
        keywords = user_input
        intent_name = user_input
        if intent_name and keywords:
            keywords_list = keywords.split(",")
            add_intent_to_json(intent_name, keywords_list)
        response_intent = keywords
        new_responses = combined_response
        if response_intent and new_responses:
            response_list = new_responses.split(",")
            add_response_to_json(response_intent, response_list)

    @database_sync_to_async
    def is_rate_limited_async(self): 
        return is_rate_limited(self.user_email)

    @database_sync_to_async
    def rate_limit_phrases_async(self, user_input): 
        return rate_limit_phrases(user_input, self.user_email)

    @database_sync_to_async
    def save_conversation(self, user_input, bot_response): 
        Conversation.objects.create(
            user_email=self.user_email,
            user_input=user_input,
            bot_response=bot_response
        )
 
    async def send_error(self, message): 
        await self.send(json.dumps({
            'type': 'error',
            'message': message
        }))

    async def handle_error(self, context, exception): 
        print(f"{context}: {str(exception)}")
        await self.send_error("An internal error occurred. Please try again.") 

    async def send_initial_state(self): 
        await self.send(json.dumps({
            'type': 'initial_state',
            'status': 'ready'
        }))
 
    async def chat_message(self, event): 
        pass
import os
from twilio.rest import Client

class WhatsAppService:
    def __init__(self):
        # Identifiants Twilio (à configurer dans les variables d'environnement ou .env)
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID', 'votre_account_sid')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN', 'votre_auth_token')
        self.whatsapp_number = os.getenv('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+14155238886')
        
    def _format_phone(self, phone_number):
        """Formate le numéro pour WhatsApp (ex: 771234567 -> whatsapp:+221771234567)"""
        if not phone_number:
            return None
        phone = str(phone_number).strip().replace(' ', '')
        if phone.startswith('whatsapp:'):
            return phone
        if phone.startswith('+221'):
            return f'whatsapp:{phone}'
        if phone.startswith('221'):
            return f'whatsapp:+{phone}'
        # Si le numéro commence par 7 ou 6 (format local Sénégal), on ajoute +221
        if phone.startswith('7') or phone.startswith('6'):
            return f'whatsapp:+221{phone}'
        return f'whatsapp:{phone}'

    def send_message(self, phone_number, message, media_url=None):
        """Envoie un message WhatsApp"""
        recipient = self._format_phone(phone_number)
        if not recipient:
            return False, "Numéro de téléphone invalide ou manquant"
            
        try:
            client = Client(self.account_sid, self.auth_token)
            message_params = {
                'from_': self.whatsapp_number,
                'body': message,
                'to': recipient
            }
            if media_url:
                message_params['media_url'] = media_url
                
            sent_message = client.messages.create(**message_params)
            return True, sent_message.sid
        except Exception as e:
            return False, str(e)

    def send_absence_alert(self, phone_number, student_name, class_name, date, status, comment=""):
        """Alerte absence/retard"""
        emoji = "⏱️" if status == "late" else "❌"
        status_text = "RETARD" if status == "late" else "ABSENCE"
        
        message = f"""{emoji} *ALERTE {status_text} - Jangal_App*

👤 Élève : {student_name}
🏫 Classe : {class_name}
📅 Date : {date}
📝 Motif : {comment if comment else 'Non précisé'}

Merci de bien vouloir régulariser la situation.
Cordialement, L'administration."""
        
        return self.send_message(phone_number, message)

    def send_payment_reminder(self, phone_number, student_name, amount, due_date):
        """Rappel de paiement"""
        message = f"""💰 *RAPPEL DE PAIEMENT - Jangal_App*

👤 Élève : {student_name}
💵 Montant dû : {amount:,.0f} FCFA
📅 Date limite : {due_date}

Merci de bien vouloir régulariser votre situation auprès de la caisse.
Cordialement, La comptabilité."""
        
        return self.send_message(phone_number, message)

    def send_bulletin_summary(self, phone_number, student_name, class_name, average, decision):
        """Envoie un récapitulatif textuel du bulletin (idéal pour réseau local)"""
        message = f"""🎓 *BULLETIN DE NOTES - Jangal_App*

👤 Élève : {student_name}
🏫 Classe : {class_name}
📊 Moyenne Générale : {average}/20
📝 Décision du conseil : *{decision}*

📌 Le bulletin détaillé avec les appréciations est disponible auprès de l'administration ou sur votre espace parent.

Cordialement, L'administration."""
        
        return self.send_message(phone_number, message)
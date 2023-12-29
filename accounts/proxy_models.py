from accounts.models import User

class ManagerUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Manager'
        verbose_name_plural = 'Manager(s)'

class ClientUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Client'
        verbose_name_plural = 'Client(s)'

        
class TeamUser(User):
    class Meta:
        proxy = True
        verbose_name = 'Team'
        verbose_name_plural = 'Team(s)'

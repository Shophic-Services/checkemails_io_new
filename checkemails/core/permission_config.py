'''
Config file for permissions for various user roles/groups
'''
from django.contrib.auth.models import Permission, Group
from accounts.models import User, UserRole

class PermissionConfig(object):
    '''
    config for permissions for various user groups
    The names below must be renamed in case the model name is renamed
    '''
    MANAGER_GROUP = [
                    "user",
                    "client",
                    ]


    TEAM_GROUP = []


    CONFIG_DATA = {
        UserRole.MANAGER: {
            'add': MANAGER_GROUP,
            'view': MANAGER_GROUP,
            'change': MANAGER_GROUP,
            'delete': MANAGER_GROUP,
        },
        UserRole.TEAM: {
            'add': TEAM_GROUP,
            'view': TEAM_GROUP,
            'change': TEAM_GROUP,
            'delete': TEAM_GROUP,
        },
    }

    def get_permissions(self, user_role_slug, get_as_obj=False):
        '''
        Returns list of permissions name 
        '''
        permission_list = []
        permission_data = self.CONFIG_DATA[user_role_slug]
        for key, value in permission_data.items():
            for model_name in value:
                permission_name = key +'_' + model_name
                permission_list.append(permission_name)
        if get_as_obj and permission_list:
            permission_obj_list = Permission.objects.filter(
                    codename__in=permission_list)
            return permission_obj_list
        return permission_list

    def set_permissions(self):
        user_type = [UserRole.MANAGER, UserRole.TEAM]
        for u_type in user_type:
            group_name = UserRole.USER_ROLE_DICT[u_type].lower()
            group_obj, created = Group.objects.get_or_create(name=group_name)
            group_permissions = self.get_permissions(u_type, True)
            if group_permissions:
                group_obj.permissions.set(group_permissions)
                group_obj.save()
            else:
                group_obj.permissions.set([])
                group_obj.save()

    @staticmethod
    def set_groups():
        user_type = [UserRole.MANAGER, UserRole.TEAM]
        groups = {}
        for u_type in user_type:
            group_name = UserRole.USER_ROLE_DICT[u_type].lower()
            group = Group.objects.filter(name=group_name).first()
            groups.update({
                u_type: group,
            })


        users = User.objects.filter(user_role__role__in=user_type)
        if users.exists():
            for user in users:
                user_type = user.user_role.role
                user.groups.add(groups[user_type])
                user.save()
        
        

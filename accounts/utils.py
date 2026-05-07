'''
utitlity for accounts
'''
import math

class CreditQuery(object):
    '''
    A class which filters the record according
    to the parameters recieved in the GET request
    '''
    def __init__(self, query_params, paginate_by, *args, **kwargs):
        # Query params from request will be a stringified dictionary
        self.query_params = query_params
        self.paginate_by = paginate_by

    def get_queryset_result(self, initial_queryset=None):
        NUM_ASSESS_PER_PAGE = self.paginate_by
        record_result = {}
        queryset = initial_queryset
        # Applies filtering
        # queryset = self.apply_filter_on_queryset(queryset, self.query_params)
        # To check for pagination
        total_record_list = queryset
        credit_count = total_record_list.count()
        page_num = 1
        # Apply pagination
        if self.query_params.get('page_action_type') == 'pagination' and self.query_params.get('page'):
            page_num = int(self.query_params.get('page'))
            
        total_num_pages = math.ceil(credit_count / NUM_ASSESS_PER_PAGE)
        if credit_count > 0 and page_num:
            start_index = (page_num - 1) * NUM_ASSESS_PER_PAGE
            end_index = start_index + NUM_ASSESS_PER_PAGE
            queryset = queryset[start_index:end_index]
        record_result['credit_list'] = queryset
        record_result.update({
                'credit_count': credit_count ,
                'total_num_pages': total_num_pages,
                'page_count': range(1, total_num_pages +  1) if total_num_pages > 1 else range(0),
                'page_dropdown_count': range(1, total_num_pages +  1) if total_num_pages > 1 else range(0),
                'current_page': page_num,
                'next_page': page_num + 1 if total_num_pages > page_num else None
        })
        if page_num and page_num > 1:
            record_result.update({
                'prev_page': page_num - 1 
                })
        else:
            record_result.update({
                'prev_page': None
            })
        if total_num_pages > 5:
            record_result['page_count'] = range(min([total_num_pages -4, page_num]), min(page_num + 4, total_num_pages) + 1)
        return record_result
    


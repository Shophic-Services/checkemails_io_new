var paginationData = localStorage.getItem("pagination_data");
var pagination_data = JSON.parse(paginationData);

var updated = []
var pageActionType = null;

if(!pagination_data){
	pagination_data = []
}

$(window).on('load',function(){
    paginationData = localStorage.getItem("pagination_data");
})

$(document).ready(function() {

    $(document).on('click', '.page-item',function(){
        var self = $(this)
        self.closest('.pagination').find('.page-item.active').removeClass('active');
        self.addClass('active');
        self.closest('.pagination').attr('data-current', self.find('.page-link').attr('data-page'));
        pageActionType = 'pagination';
        ajax_send();
    })
    
})


function get_filter_data(){

    var filter_set = new Object();
    filter_set['page'] = $('.pagination').attr('data-current');
    localStorage.setItem("pagination_data", JSON.stringify(filter_set));
    paginationData = localStorage.getItem("pagination_data");
    
}


function ajax_send(){

    $('div#loader').removeClass('fadeOut')
    get_filter_data();
    search_pagination_data = JSON.parse(paginationData);
    search_pagination_data['page_action_type'] = pageActionType;
    $.ajax({
        url: window.location.pathname + '?' + 'search_pagination_data=' + JSON.stringify(search_pagination_data),
        success: function(response) {
            $( ".search-results" ).html( response );
            feather.replace()
            setTimeout(function () {$('div#loader').addClass('fadeOut');}, 100);
        },
        error: function(error) {
            console.log('Something went wrong');
        }
    });
    
}

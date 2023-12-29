$(document).ready(function() {
    $(window).keydown(function(event){
      if(event.keyCode == 13) {
        event.preventDefault();
        // checker()
        return false;
      }
    });
if($('#email-id').length > 0){

  $('#email-id').multiple_emails();
}
  });
      function checker(){   
        $('.multiple_emails-container.valid-container-box li').html('-')
        $('.multiple_emails-container.invalid-container-box li').html('-')
        $('.total-count').html(0)
                    $('.valid-count').html(0)
                    $('.invalid-count').html(0)
  $("#error-msg").addClass('d-none');
  
  $(".search-content").addClass('disabled-div');
  $('.search-submit-icon').addClass('arrowsRotate');
          $.ajax('', {
          method: "POST",
          data: $('form').serialize(),
          success: function(response) {
            
            $(".search-content").removeClass('disabled-div');
            $('.search-submit-icon').removeClass('arrowsRotate');
              var total_count = 0
              var valid_count = 0
              var invalid_count = 0
                if (response.errors == ''){
                  
                  valid_html = ''
                  invalid_html = ''
                  
                  
                  $.map(response.data, function(element, index){
                    if(element.email_verified){

                      valid_html += '<li class="multiple_emails-email valid-email"><span class="email_name">'+ element.email +'</span></li>'
                      valid_count += 1
                    }
                    else{
                      invalid_html += '<li class="multiple_emails-email invalid-email"><span class="email_name">'+ element.email +'</span></li>'
                      invalid_count += 1
                    }
                    total_count += 1
                  })
                  $(".valid-box").html(valid_html);
                  $(".invalid-box").html(invalid_html);
                    // $("#success-msg").show();
                    // $("#error-msg").hide();
                    $('.multiple_emails-container').not('.valid-container-box').not('.invalid-container-box').remove()
                    $('.multiple_emails-ul').not('.valid-box').not('.invalid-box').remove()
                    $('#email-id').val('[]')
                    $('#email-id').multiple_emails();
                    $('.total-count').html(total_count)
                    $('.valid-count').html(valid_count)
                    $('.invalid-count').html(invalid_count)
                    // $("#success-msg").html("Email Address is okk");
                    
                }
                else{
                    
                  
                  $("#error-msg").removeClass('d-none');
                  $("#error-msg").html(response.errors);
                  // errorMsg.style.display = 'block';
                  // emailId.style.border = '2px solid #ff2851';
                }
                  
          },
          error: function(response){
                  
            $("#error-msg").removeClass('d-none');
            $("#error-msg").html(response.errors);
            
            $(".search-content").removeClass('disabled-div');
            $('.search-submit-icon').removeClass('arrowsRotate');
          }
          })
              
  
  }
  function single_checker(){   

    var regex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
    if (!regex.test($('#single-email-id').val())){
      $('#single-email-id').addClass('multiple_emails-error')
      return
    }
    $('#single-email-id').removeClass('multiple_emails-error')
    $('.multiple_emails-container.valid-container-box li').remove()
    $('.multiple_emails-container.invalid-container-box li').remove()
$("#error-msg").addClass('d-none');
$('.single-invalid-box').addClass('d-none')
                $('.single-valid-box').addClass('d-none')
              $('.result-highlights').addClass('d-none')

$("#loader").removeClass('fadeOut');
      $.ajax('', {
      method: "POST",
      data: $('form').serialize(),
      success: function(response) {
        
          $("#loader").addClass('fadeOut');
          var total_count = 0
          var valid_count = 0
          var invalid_count = 0
            if (response.errors == ''){
              
              valid_html = ''
              invalid_html = ''
              
              
              $.map(response.data, function(element, index){
                if(element.email_verified){

                  valid_html += '<li class="multiple_emails-email valid-email"><span class="email_name">'+ element.email +'</span></li>'
                  valid_count += 1
                }
                else{
                  invalid_html += '<li class="multiple_emails-email invalid-email"><span class="email_name">'+ element.email +'</span></li>'
                  invalid_count += 1
                }
                total_count += 1
              })
              $(".valid-box").html(valid_html);
              $(".invalid-box").html(invalid_html);
              if(invalid_count > 0){
                $('.single-invalid-box').removeClass('d-none')
              }
              if(valid_count > 0){
                $('.single-valid-box').removeClass('d-none')
              }
              $('.result-highlights').removeClass('d-none')
                // $("#success-msg").show();
                // $("#error-msg").hide();
                
                $('#single-email-id').val('')
                // $("#success-msg").html("Email Address is okk");
                
            }
            else{
                
              $('.result-highlights').removeClass('d-none')
                
              $("#error-msg").removeClass('d-none');
              $("#error-msg").html(response.errors + '<br>' + response.sub_errors);
              // errorMsg.style.display = 'block';
              // emailId.style.border = '2px solid #ff2851';
            }
              
      },
      error: function(response){
              
        $("#error-msg").removeClass('d-none');
        $("#error-msg").html(response.errors);
        
        $("#loader").addClass('fadeOut');
      }
      })
          

}
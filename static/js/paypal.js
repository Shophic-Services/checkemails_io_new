var csrftoken = $("[name=csrfmiddlewaretoken]").val();
    
$('#paypal-button').on('click', function(){
    $('.payment-box').removeClass('active')
    $(this).addClass('active')
    $('#card-div').addClass('d-none')
    $('#paypal-div').removeClass('d-none')
})
$('#card-button').on('click', function(){
    $('.payment-box').removeClass('active')
    $(this).addClass('active')
    $('#card-div').removeClass('d-none')
    $('#paypal-div').addClass('d-none')
})
plan_id = $('input[name="plan"]').val()
paypal.Buttons({
style: {
label: 'paypal',
layout: 'horizontal'
},
createOrder: function () {
    
    return fetch('/subscriptions/plan-paypal-create/'+ plan_id +'/', {
        method: 'post',
        headers: {
            'content-type': 'application/json',
            "X-CSRFToken": csrftoken
        }
    }).then(res => {
        // console.log("data here"+res.clone.json())
        
        return res.json()

    }).then( data=> {
        // console.log("id here"+data.clone.id)
        return data.id; // Use the key sent by your server's response, ex. 'id' or 'token'
    }).catch(error =>{
        window.location = '/subscriptions/payment-failure/'
    // console.log('error:')
    // console.error(error);
    // fetch('failure-page',{
    //     method:'get',

    // }).catch(error=>{
    //     console.error(error)
    // })
    });

},
onApprove: function (data) {
    return fetch('/subscriptions/plan-paypal-buy/'+ plan_id +'/', {
        method: 'post',
        headers: {
            'content-type': 'application/json',
            "X-CSRFToken": csrftoken
        },
        body: JSON.stringify({
            orderID: data.orderID
        })
    }).then( res=> {
        return res.json();
    }).then(function (details) { 
        // fetch('success-page',{
        //     method:'get',

        // }).catch(error=>{
        //     console.error(error)
        // })
        
        window.location = '/subscriptions/payment-success/';
        
//   alert('Transaction funds captured from' + details.payer_given_name);

    }).catch(error =>{
        // fetch('failure-page',{
        //     method:'get',

        // }).catch(error=>{
        //     console.error(error)
        // })
        window.location = '/subscriptions/payment-failure/'
        // console.log('error:')
        // console.error(error);
        });
    }
}).render('#paypal-button-container');
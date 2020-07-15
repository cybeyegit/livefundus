odoo.define('website_loyalty.website_loyalty', function (require) {
    "use strict";
    
    var ajax = require('web.ajax');
    
$(document).ready(function() {

if (typeof $('#auto_remove').prev().attr('href') =='string'){	
	location.href=$('#auto_remove').prev().attr('href');
	}
	
    var html = $('#cart_total').html()
    setInterval(function() {
        if ($('#cart_total').html() != html) {
            html = $('#cart_total').html()
            $("#sale_order_can_make_points").addClass('bg-primary');

            setTimeout(function() {

                $("#sale_order_can_make_points").load(location.href + " #sale_order_can_make_points");

                $("#sale_order_can_make_points").removeClass('bg-primary');

            }, 200);

        }

    }, 1000);

    function model_show() {
        $('#modal_confimation').appendTo('body').modal('show').on('shown.bs.modal', function() {

        }).on('hidden.bs.modal', function() {


            location.reload(true);
        });
    }

    $('#loyality_confimation').on('click', function() {


        ajax.jsonRpc('/myloyality/confimation/', 'call', {})
            .then(function(response) {

                document.body.innerHTML += response.toString();
                model_show();

            });
    });

    $('._o_link_redeem_rule').on('click', function() {

        $('#redeem_rule_modal').appendTo('body').modal('show').on('shown.bs.modal', function() {

            $('#modal_confimation').hide();


        })
    });

    $('.one_time_redeem_example').on('click',

        function() {
            $(this).parent().parent().find('.one_time_redeem_example_div').show({
                direction: "left"
            }, 500);

        });
    $('.partial_redeem_example').on('click',

        function() {
            $(this).parent().parent().find('.partial_redeem_example_div').show({
                direction: "right"
            }, 500);

        });


    $(".one_time_redeem_example_div").delegate("._o_one_time_redeem_policy_example_div_close", "click", function() {
        $('.one_time_redeem_example_div').hide({
            direction: "right"
        }, 500);

    });

    $(".partial_redeem_example_div").delegate("._o_partial_redeem_example_div_close", "click", function() {
        $('.partial_redeem_example_div').hide({
            direction: "left"
        }, 500);
    });

});
});

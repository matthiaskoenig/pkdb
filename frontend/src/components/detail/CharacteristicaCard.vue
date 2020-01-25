<template>
    <div :class="card_class">

        <v-badge inline left light overlap color="#BBBBBB">
            <span slot="badge">{{ data.count }}</span>
            <strong>{{ data.measurement_type }}</strong>
        </v-badge>
        <br />

        <!--
        <strong>{{ data.measurement_type }}</strong><br />
        -->
        <span v-if="data.choice">
            <span v-if="data.choice=='Y'"><v-icon small color="success">fa fa-check-circle</v-icon></span>
            <span v-if="data.choice=='N'"><v-icon small color="error">fa fa-times-circle</v-icon></span>
            <span v-if="(data.choice=='F') || (data.choice =='homo sapiens')"><v-icon small color="primary">fa fa-female</v-icon></span>
            <span v-if="(data.choice=='M') || (data.choice =='homo sapiens')"><v-icon small color="primary">fa fa-male</v-icon></span>
            {{ data.choice }}
        </span>
        <span v-else>
            <span><v-icon small color="black">fa fa-bolt</v-icon></span>
        </span>
        <span v-if="value || error">
            {{ value }} <span v-if="error">{{ error }}</span><br />
            <span v-if="data.unit">[{{ data.unit }}]</span>
        </span>
        <span v-else-if="!value & !error & !data.choice & !data.substance">
            <v-icon small title='missing information for characteristica'>{{ faIcon("na") }}</v-icon>
        </span>

    </div>
</template>

<script>
    import {lookupIcon} from "@/icons"

    export default {
        name: "CharacteristicaCard",
        props: {
            data: Object,
        },
        computed: {
            count() {
                if (!this.data.count){
                    return 1;  // individual has no count ? FIXME bug
                } else {
                    return this.data.count
                }
            },
            error() {
                var value = null;

                // min, max
                if (this.data.min || this.data.max){
                    value = '(' + (this.data.min ? this.toNumber(this.data.min) : '')  + ' - ' + (this.data.max ? this.toNumber(this.data.max) : '') + ')'
                }
                // sd, se, cv, unit
                var error_fields = ['sd', 'se', 'cv'];
                for (var i=0; i<error_fields.length; i++){
                    var field = error_fields[i];
                    if (this.data[field]){
                        const token = ' ± ' + this.toNumber(this.data[field]) + ' ' + field.toUpperCase() + '';
                        if (value){
                            value += token
                        } else {
                            value = token
                        }
                    }
                }
                return value;
            },

            value() {
                var value = null;
                // value, mean, median

                if (this.data.value){
                    value = this.toNumber(this.data.value);
                } else if (this.data.mean){
                    value = this.toNumber(this.data.mean);
                }
                if (this.data.median){
                    if (value){
                        value += '(median ' + this.toNumber(this.data.median) + ')'
                    } else {
                        value = 'median ' + this.toNumber(this.data.median)
                    }
                }
                return value;
            },

            card_class() {
                if (this.value){
                    return "characteristica_card_wide"
                }
                else {
                    return "characteristica_card"
                }

            }
        },
        methods: {
            faIcon: function (key) {
                return lookupIcon(key)
            },
            toNumber: function(num){
                // round to two numbers
                return +(Math.round(num + "e+2")  + "e-2");
            },
        },
        calculated: {
        }
    }
</script>

<style scoped lang="css">
    .attr-characteristica {
        background-color: lightgray;
    }

    .characteristica_card {
        padding-top: 20px;
        padding-right: 10px;
        padding-left: 10px;
        margin-bottom: 10px;
        width: 110px;
        height: 85px;

        border-style: none;
        border-width: thin;
        border-color: gray;
    }

    .characteristica_card_wide {
        padding-top: 20px;
        padding-right: 10px;
        padding-left: 10px;
        margin-bottom: 10px;
        width: 200px;
        height: 85px;

        border-style: none;
        border-width: thin;
        border-color: gray;
    }
</style>
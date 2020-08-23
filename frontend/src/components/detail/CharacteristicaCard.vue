<template>
    <div :class="card_class">

      <span v-if="!(data.choice && data.choice.sid)">
        <v-badge inline right light overlap color="#BBBBBB">
            <span slot="badge">{{ data.count }}</span>
            <node-element :data="data.measurement_type"/>
        </v-badge>
      </span>

      <br />

        <span v-if="data.choice && data.choice.sid">
          <!--
            <span v-if="data.choice.sid=='Y'"><v-icon small color="success">fa fa-check-circle</v-icon></span>
            <span v-if="data.choice.sid=='N'"><v-icon small color="error">fa fa-times-circle</v-icon></span>
            -->
          <v-badge inline right light overlap color="#BBBBBB">
            <span slot="badge">{{ data.count }}</span>
            <node-element :data="data.choice"/>
        </v-badge>

            <span v-if="(data.choice.sid=='female') || (data.choice.sid =='homo-sapiens')"><v-icon small color="primary">fa fa-female</v-icon></span>
            <span v-if="(data.choice.sid=='male') || (data.choice.sid =='homo-sapiens')"><v-icon small color="primary">fa fa-male</v-icon></span>
            <span v-if="(data.choice.sid=='smoking-yes')"><v-icon small color="red">fa fa-smoking</v-icon></span>
            <span v-if="(data.choice.sid=='smoking-no')"><v-icon small color="green">fa fa-smoking-ban</v-icon></span>
            <span v-if="(data.choice.sid=='medication-yes')"><v-icon small color="red">fa fa-tablets</v-icon></span>
            <span v-if="(data.choice.sid=='medication-no')"><v-icon small color="green">fa fa-tablets</v-icon></span>

            <span v-if="(data.choice.sid=='healthy-yes')"><v-icon small color="green">fa fa-check-circle</v-icon></span>
            <span v-if="(data.choice.sid=='healthy-no')"><v-icon small color="red">fa fa-times-circle</v-icon></span>

        </span>
        <span v-if="value || error">
            {{ value }} <span v-if="error">{{ error }}</span><br />
            <span v-if="data.unit" class="font-weight-italics">{{ data.unit }}</span>
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
                let value = null;

                // min, max
                if (this.data.min || this.data.max){
                  if (this.data.min && this.data.max) {
                    value = '[' + this.toNumber(this.data.min) + '-' + this.toNumber(this.data.max) + ']';
                  }
                  if (this.data.min && !this.data.max){
                    value = '[>' + this.toNumber(this.data.min) + ']';
                  }
                  if (!this.data.min && this.data.max){
                    value = '[<' + this.toNumber(this.data.max) + ']';
                  }
                }
                // sd, se, cv, unit
                let error_fields = ['sd', 'se', 'cv'];
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
<template>

    <v-card

        flat
        tile
        height="100%"
        width="100%"
        @click="update_details"


        class="characteristica_card parent_color"
        align="start">
      <v-container fluid class="pt-1 pb-1">
        <v-row>
          <v-badge v-if="data.count" inline color="#BBBBBB" right>
            <span slot="badge">{{ count_label }}</span>
            <node-element  v-if="!data.choice" :data="data.measurement_type"/>
            <span v-if="data.choice">
                <span v-if="(data.choice.sid=='female')"><v-icon small left color="primary">fa fa-female</v-icon></span>
                <span v-if="(data.choice.sid=='male')"><v-icon small left color="primary">fa fa-male</v-icon></span>
                <span v-if="(data.choice.sid=='homo-sapiens')"><v-icon small color="primary">fa fa-female</v-icon><v-icon small left color="primary">fa fa-male</v-icon></span>
                <span v-if="(data.choice.sid=='smoking-yes')"><v-icon small left color="red">fa fa-smoking</v-icon></span>
                <span v-if="(data.choice.sid=='smoking-no')"><v-icon small left color="green">fa fa-smoking-ban</v-icon></span>
                <span v-if="(data.choice.sid=='medication-yes')"><v-icon small left color="red">fa fa-tablets</v-icon></span>
                <span v-if="(data.choice.sid=='medication-no')"><v-icon small left color="green">fa fa-tablets</v-icon></span>
                <span v-if="(data.choice.sid=='healthy-yes')"><v-icon small left color="green">fa fa-check-circle</v-icon></span>
                <span v-if="(data.choice.sid=='healthy-no')"><v-icon small left color="red">fa fa-times-circle</v-icon></span>

                <node-element :data="data.choice"/>
            </span>
          </v-badge>
          <span v-else>
            <node-element  v-if="!data.choice" :data="data.measurement_type"/>
            <node-element v-if="data.choice" :data="data.choice"/>
          </span>
        </v-row>

        <v-row>
            <object-chip
                v-if="data.substance"
                :object="data.substance"
                otype="substance"
                :search="search"
                margin="ma-0 pb-0 mr-2"
            />


          <span v-if="value || error">
          <span>
            <object-chip
                v-if="(data.substance !== null) & (!data.measurement_type.sid === 'abstinence')"
                :object="data.substance"
                otype="substance"
                :search="search"
                margin="ma-0 pb-0"
            />
          </span>
            {{ value }} <span v-if="error">{{ error }}</span>
            <span v-if="data.unit"> [{{ data.unit }}]</span>

          </span>

          <span v-if="!value & !error & (!data.choice) & !data.substance">
              <v-icon small  title='missing information for characteristica'>{{ faIcon("na") }}</v-icon>
          </span>
        </v-row>
      </v-container>

    </v-card>
</template>

<script>
    import {ApiInteractionMixin} from "../../apiInteraction";
    import {IconsMixin} from "../../icons";


    export default {
        name: "CharacteristicaCard",
        mixins: [ApiInteractionMixin, IconsMixin],
        props: {
            data: Object,
        },
        computed: {
            search(){
              return this.highlight
            },
            count() {
                if (!this.data.count){
                    return 1;  // individual has no count ? FIXME bug
                } else {
                    return this.data.count;
                }
            },
            subject_count(){
              if (this.data.group_count){
                return this.data.group_count
              }
              return this.count
            },
            count_label(){
                if (this.subject_count == this.count) {
                  return this.subject_count.toString()
                } else if (this.subject_count < this.count){
                    return ">" + this.subject_count.toString()
                } else {
                  return this.count.toString() + "/" + this.subject_count.toString()
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
                for (let i=0; i<error_fields.length; i++){
                    let field = error_fields[i];
                    if (this.data[field]){
                        const token = ' ± ' + this.toNumber(this.data[field]) + ' ' + field.toUpperCase() + '';
                        if (value){
                            value += token
                        } else {
                            value = token
                        }
                        continue;
                    }
                }
                return value;
            },

            value() {
                let value = null;
                // value, mean, median

                if (this.data.value){
                    value = this.toNumber(this.data.value);
                } else if (this.data.mean){
                    value = this.toNumber(this.data.mean);
                }
                if (this.data.median){
                    if (!value){
                        value = 'median ' + this.toNumber(this.data.median)
                    }
                }
                return value;
            },
            card_class() {
              return "characteristica_card"
            }
        },
        methods: {

          update_details() {
            if (this.data.choice) {
              this.getInfo(this.data.choice.sid, "info_node")

            } else {
            this.getInfo(this.data.measurement_type.sid, "info_node")
            }
          },
          toNumber: function(num){
                // round to two digits
              let number = num
              if (num > 0.1){
                number = +(Math.round(num + "e+2")  + "e-2");
              } else {
                number = num.toExponential(2);
              }

              /*
              if (!number){
                number = num;
                number = Number.toExponential(num)
              }
              */
              return number
            },
        },
        calculated: {
        }
    }
</script>

<style scoped lang="css">
    .characteristica_card {
      font-size: small;
      padding-left: 10px;
    }
    .parent_color{
      background-color: inherit;
    }
</style>
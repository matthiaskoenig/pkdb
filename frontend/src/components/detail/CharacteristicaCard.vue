<template>
    <div class="characteristica_card">

        <v-badge right color="black" left>
            <span slot="badge">{{ count }}</span>
            <span class="attr attr-characteristica">{{ data.category }}</span><br />

            <span v-if="data.choice">
                <span v-if="data.choice=='Y'"><v-icon color="success">fa fa-check-circle</v-icon></span>
                <span v-if="data.choice=='N'"><v-icon color="error">fa fa-times-circle</v-icon></span>
                <span v-if="(data.choice=='F') || (data.choice =='homo sapiens')"><v-icon color="primary">fa fa-female</v-icon></span>
                <span v-if="(data.choice=='M') || (data.choice =='homo sapiens')"><v-icon color="primary">fa fa-male</v-icon></span>
                {{ data.choice }}
            </span>
            <span v-if="value">
                <strong>{{ value }}<span v-if="data.unit"> [{{ data.unit }}]</span></strong><br />
                <span v-if="error">{{ error }}</span>
            </span>
        </v-badge>
    </div>

</template>

<script>
    import {lookup_icon} from "@/icons"

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
                    value = '[' + (this.data.min ? this.data.min : '')  + ' - ' + (this.data.max ? this.data.max : '') + ']'
                }
                // sd, se, cv, unit
                var error_fields = ['sd', 'se', 'cv'];
                for (var i=0; i<error_fields.length; i++){
                    var field = error_fields[i];
                    if (this.data[field]){
                        const token = ' ± ' + this.data[field] + ' (' + field + ')';
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
                    value = this.data.value
                } else if (this.data.mean){
                    value = this.data.mean
                }
                if (this.data.median){
                    if (value){
                        value += '(median ' + this.data.median + ')'
                    } else {
                        value = 'median ' + this.data.median
                    }
                }
                return value;
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped lang="css">
    .attr-characteristica {
        background-color: lightgray;
    }

    .characteristica_card {
        padding-top: 25px;
        padding-right: 10px;
        padding-left: 30px;
        margin-bottom: 20px;
        width: 110px;
        height: 85px;

        border-style: none;
        border-width: thin;
        border-color: gray;
    }
</style>
<template>
    <div class="characteristica_card">
    <v-badge right color="red">
        <span slot="badge">{{ data.count }}</span>
        <span class="attribute">{{ data.category }}</span><br />
        <span v-if="data.choice">
            <span v-if="data.choice=='Y'"><v-icon color="success">fa fa-check-circle</v-icon></span>
            <span v-if="data.choice=='N'"><v-icon color="error">fa fa-times-circle</v-icon></span>
            <span v-if="data.choice=='F'"><v-icon color="primary">fa fa-female</v-icon></span>
            <span v-if="data.choice=='M'"><v-icon color="primary">fa fa-male</v-icon></span>
            {{ data.choice }}
        </span>
        <span v-if="value"><strong>{{ value }}</strong></span>&nbsp; <span v-if="error">{{ error }}</span>&nbsp; <span v-if="data.unit"> [<strong>{{ data.unit }}</strong>]</span>
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
            error() {
                var value = null;

                // min, max
                if (this.data.min || this.data.max){
                    value = '[' + (this.data.min ? this.data.min : '')  + ' - ' + (this.data.max ? this.data.max : '') + ']'
                }
                // sd, se, cv, unit
                for (var field in ['sd', 'se', 'cv']){
                    if (this.data[field]){
                        if (value){
                            value += field + '=' + this.data[field]
                        } else {
                            value = field + '=' + this.data[field]
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
    .attribute {
        font-weight: bold;
        background-color: lightgray;
    }

    .characteristica_card {
        padding-top: 20px;
        padding-right: 30px;
        padding-left: 20px;
        width: 100px;
        height: 100px;
        // background-color: #0d47a1;

        border-style: groove;
        border-width: thin;
        border-color: gray;
    }
</style>
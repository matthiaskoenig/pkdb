<template>
    <div class="characteristica-card">
        <v-card>
        <v-layout id="study-info">
            <v-flex xs2>
                <v-badge right color="red">
                    <span slot="badge">{{ data.count }}</span>
                    <v-icon>{{ icon('characteristica') }}</v-icon>
                </v-badge>&nbsp;
            </v-flex>
            <v-flex xs4>
                <strong>{{ data.category }}</strong><span v-if="data.unit"> [{{ data.unit }}]</span>
            </v-flex>
            <v-flex xs2>
                <span v-if="data.choice">{{ data.choice }}</span>
            </v-flex>
            <v-flex xs2>
                <span v-if="value">{{ value }}</span>
            </v-flex>
            <!--
            <v-flex xs2>
                {{ data }}
            </v-flex>
            -->
        </v-layout>
        </v-card>
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

                // min, max
                if (this.data.min || this.data.max){


                    const min_value = '(' + (this.data.min ? this.data.min : '')  + ' - ' + (this.data.max ? this.data.max : '') + ')'
                    if (value){
                        value += ' ' + min_value
                    } else {
                        value = min_value
                    }
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
            }
        },
        methods: {
            icon: function (key) {
                return lookup_icon(key)
            },
        }
    }
</script>

<style scoped>
</style>

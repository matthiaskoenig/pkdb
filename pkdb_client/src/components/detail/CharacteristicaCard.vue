<template>
    <div class="characteristica-card">
        {{ data }}
        <!--
        <md-card :class="'md-card ' + color">
            <md-ripple>

                <md-card-content class="md-card-content">
                <div class="md-title">{{characteristica_no_options.choice}}</div>
                <div class="md-subhead title_sub">{{characteristica_no_options.category}}</div>
                <div class="card-reservation">
                    <div v-for="(value, key) in characteristica_clean" :key="key">
                        <div class="values">
                            <span>{{value}} </span>
                            <div class="key">{{key}}</div>
                        </div>

                    </div>
                </div>

            </md-card-content>
            </md-ripple>
        </md-card>
        -->
    </div>
</template>

<script>

    export default {
        name: "CharacteristicaCard",
        props: {
            data: Object,
            resource_url: String,
        },
        computed: {
        }
    }
</script>

<style scoped>
</style>

<template>
    <div id="descriptions" v-if="descriptions && descriptions.length>0">
        <div v-for="description in descriptions" :key="description.pk" style="text-align: justify; color: white">

                <v-avatar title="description" :size="32">
                  <v-icon small>fas fa-align-left</v-icon>&nbsp;&nbsp;
                </v-avatar>
                {{ description.text }}
        </div>
    </div>
</template>

<script>
    export default {
        name: "Descriptions",
        props: {
            descriptions: {
                type: Array,
            }
        }
    }
</script>

<style scoped>
 .white_text{
   color: white; }

</style>
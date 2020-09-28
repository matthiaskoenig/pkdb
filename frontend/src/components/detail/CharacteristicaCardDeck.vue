<template>
    <span>
        <v-layout d-flex flex-wrap >
            <span v-for="item in sortedCharacteristica.choices" :key="item.pk">
                <characteristica-card :data="item" />

            </span>
            <span v-for="item in sortedCharacteristica.values" :key="item.pk">

                <characteristica-card :data="item" />
            </span>
        </v-layout>
    </span>

</template>

<script>
    import CharacteristicaCard from './CharacteristicaCard';

    export default {
        name: "CharacteristicaCardDeck",
        components: {
            CharacteristicaCard
        },
        props: {
            characteristica: {
                type: Array,
                required: true
            },
        },
        methods: {
            f_sort : function(a, b) {
                if (a.choice.label && !b.choice.label){
                  return 1
                } else if (!a.choice.label && b.choice.label) {
                  return -1
                } else if (a.choice.label && b.choice.label) {
                  if (a.choice.label > b.choice.label) {
                    return 1;
                  } else if (a.choice.label < b.choice.label) {
                    return -1;
                  }
                } else if (!a.choice.label && !b.choice.label){
                if (a.measurement_type.label > b.measurement_type.label) {
                  return 1;
                } else if (a.measurement_type.label < b.measurement_type.label) {
                  return -1;
                }
                return 0;
              }

            },
        },
        computed: {

            sortedCharacteristica: function () {
                // split characteristica in choices and values and sort them
                var choices = []
                var values = []
                for (var index in this.characteristica){
                    var c = this.characteristica[index]
                    if (c.choice){
                        choices.push(c);
                    } else {
                        values.push(c);
                    }
                }

                return {
                    'choices': choices.sort(this.f_sort),
                    'values': values.sort(this.f_sort)
                };
            }
        }
    }
</script>

<style scoped>
</style>